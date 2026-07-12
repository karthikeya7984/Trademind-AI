"""
migrate_sqlite_to_postgres.py
─────────────────────────────
Migrates all data from the existing SQLite database (trademind.db)
to the Render PostgreSQL database.

Usage (run from the backend/ directory):
    python migrate_sqlite_to_postgres.py

Requirements:
    pip install sqlalchemy asyncpg aiosqlite psycopg2-binary

What it does:
  - Connects to SQLite (source)
  - Connects to PostgreSQL (target)
  - Reads every table in dependency order (parents before children)
  - Inserts rows into PostgreSQL
  - Skips rows that already exist (ON CONFLICT DO NOTHING)
  - Preserves all PKs, FKs, and timestamps
  - Prints progress and a final summary
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

load_dotenv()  # loads backend/.env

# ── Connection URLs ────────────────────────────────────────────────────────────
SQLITE_URL   = "sqlite+aiosqlite:///./trademind.db"
POSTGRES_URL = os.environ["DATABASE_URL"]  # must be set in .env

# Tables in insertion order (parents before children to satisfy FK constraints)
TABLES = [
    "users",
    "otp_tokens",
    "email_tokens",
    "login_activity",
    "announcements",
    "paper_trading",
    "prediction_history",
    "portfolio",
    "watchlist",
    "trade_history",
    "ai_chat_history",
    "notifications",
]


def _coerce_row(row: dict) -> dict:
    """
    Ensure datetime strings from SQLite are proper datetime objects
    and that None values are preserved correctly for PostgreSQL.
    """
    result = {}
    for k, v in row.items():
        if isinstance(v, str):
            # Try to parse ISO datetime strings SQLite stores as TEXT
            for fmt in ("%Y-%m-%d %H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S%z",
                        "%Y-%m-%d %H:%M:%S.%f",   "%Y-%m-%d %H:%M:%S"):
                try:
                    dt = datetime.strptime(v, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    result[k] = dt
                    break
                except ValueError:
                    continue
            else:
                result[k] = v
        else:
            result[k] = v
    return result


async def migrate_table(
    src_session: AsyncSession,
    dst_session: AsyncSession,
    table: str,
) -> tuple[int, int]:
    """
    Copy all rows from `table` in SQLite → PostgreSQL.
    Returns (rows_migrated, rows_skipped).
    """
    # Read all rows from SQLite
    result = await src_session.execute(text(f'SELECT * FROM "{table}"'))
    rows = result.mappings().all()

    if not rows:
        print(f"  [{table}] — empty, skipping")
        return 0, 0

    migrated = 0
    skipped  = 0

    for raw_row in rows:
        row = _coerce_row(dict(raw_row))
        columns      = ", ".join(f'"{c}"' for c in row.keys())
        placeholders = ", ".join(f":{c}" for c in row.keys())
        # ON CONFLICT DO NOTHING — safe to re-run without duplicates
        stmt = text(
            f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders}) '
            f'ON CONFLICT DO NOTHING'
        )
        try:
            await dst_session.execute(stmt, row)
            migrated += 1
        except Exception as e:
            print(f"  [{table}] WARN row skipped — {e}")
            skipped += 1

    await dst_session.commit()
    return migrated, skipped


async def verify_postgres_tables(dst_engine) -> list[str]:
    """Return list of tables that exist in PostgreSQL."""
    async with dst_engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ))
        return [r[0] for r in result.fetchall()]


async def main():
    print("=" * 60)
    print("  TradeMind AI — SQLite → PostgreSQL Migration")
    print("=" * 60)

    # ── Create engines ─────────────────────────────────────────────────────────
    print("\n[1/4] Connecting to SQLite …")
    try:
        src_engine = create_async_engine(SQLITE_URL, echo=False)
        async with src_engine.connect() as c:
            await c.execute(text("SELECT 1"))
        print("      ✓ SQLite connected")
    except Exception as e:
        print(f"      ✗ SQLite connection failed: {e}")
        sys.exit(1)

    print("[2/4] Connecting to PostgreSQL …")
    try:
        dst_engine = create_async_engine(
            POSTGRES_URL,
            echo=False,
            pool_pre_ping=True,
            connect_args={"ssl": "require"},
        )
        async with dst_engine.connect() as c:
            await c.execute(text("SELECT 1"))
        print("      ✓ PostgreSQL connected")
    except Exception as e:
        print(f"      ✗ PostgreSQL connection failed: {e}")
        sys.exit(1)

    # ── Verify target tables exist ─────────────────────────────────────────────
    print("[3/4] Verifying PostgreSQL schema …")
    existing_tables = await verify_postgres_tables(dst_engine)
    missing = [t for t in TABLES if t not in existing_tables]
    if missing:
        print(f"      ✗ Missing tables in PostgreSQL: {missing}")
        print("      Run 'alembic upgrade head' first, then re-run this script.")
        sys.exit(1)
    print(f"      ✓ All {len(TABLES)} tables present")

    # ── Migrate data ───────────────────────────────────────────────────────────
    print("[4/4] Migrating data …\n")

    SrcSession = async_sessionmaker(src_engine, class_=AsyncSession, expire_on_commit=False)
    DstSession = async_sessionmaker(dst_engine, class_=AsyncSession, expire_on_commit=False)

    total_migrated = 0
    total_skipped  = 0
    summary        = []

    async with SrcSession() as src_session, DstSession() as dst_session:
        for table in TABLES:
            print(f"  Migrating [{table}] …", end=" ", flush=True)
            try:
                migrated, skipped = await migrate_table(src_session, dst_session, table)
                total_migrated += migrated
                total_skipped  += skipped
                summary.append((table, migrated, skipped))
                print(f"✓  {migrated} rows migrated, {skipped} skipped")
            except Exception as e:
                print(f"✗  ERROR — {e}")
                summary.append((table, 0, 0))

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Migration Summary")
    print("=" * 60)
    print(f"  {'Table':<25} {'Migrated':>10} {'Skipped':>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*10}")
    for table, m, s in summary:
        print(f"  {table:<25} {m:>10} {s:>10}")
    print(f"  {'-'*25} {'-'*10} {'-'*10}")
    print(f"  {'TOTAL':<25} {total_migrated:>10} {total_skipped:>10}")
    print("=" * 60)
    print("\n✅  Migration complete! Verify your application at http://localhost:8000/health\n")

    await src_engine.dispose()
    await dst_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
