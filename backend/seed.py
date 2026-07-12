"""
Database seed script.

Admin password setup:
  Set ADMIN_PASSWORD_HASH in backend/.env to a bcrypt hash.
  Generate one with:
    python -c "from app.core.security import hash_password; print(hash_password('YourPassword'))"

  Then add to .env:
    ADMIN_PASSWORD_HASH=<the hash>
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select
from app.core.database import Base
from app.core.security import hash_password
from app.models.models import User, Portfolio, Watchlist, PaperTrading
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"ssl": "require"} if settings.DATABASE_URL.startswith("postgresql") else {},
)
Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as db:
        # Check if admin already exists
        existing = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        if existing.scalar_one_or_none():
            print(f"[SKIP] Admin {settings.ADMIN_EMAIL} already exists, skipping.")
        else:
            if not settings.ADMIN_PASSWORD_HASH:
                raise RuntimeError(
                    "ADMIN_PASSWORD_HASH is not set in .env\n"
                    "Generate it with:\n"
                    "  python -c \"from app.core.security import hash_password; print(hash_password('YourPassword'))\"\n"
                    "Then add ADMIN_PASSWORD_HASH=<hash> to backend/.env"
                )
            admin = User(
                name="Administrator",
                email=settings.ADMIN_EMAIL,
                password_hash=settings.ADMIN_PASSWORD_HASH,
                role="admin",
                account_type="enterprise",
                is_verified=True,
            )
            db.add(admin)
            await db.flush()
            db.add(PaperTrading(user_id=admin.id, balance=1_000_000))
            print(f"[OK] Admin created: {settings.ADMIN_EMAIL}")

        # Demo trader
        existing_demo = await db.execute(select(User).where(User.email == "demo@trademind.ai"))
        if not existing_demo.scalar_one_or_none():
            trader = User(
                name="Demo Trader",
                email="demo@trademind.ai",
                password_hash=hash_password("Demo@123"),
                role="user",
                account_type="pro",
                is_verified=True,
            )
            db.add(trader)
            await db.flush()
            db.add(PaperTrading(user_id=trader.id, balance=100_000))

            for sym, qty, price in [("AAPL", 10, 175.0), ("TSLA", 5, 250.0), ("NVDA", 3, 480.0), ("MSFT", 8, 380.0)]:
                db.add(Portfolio(user_id=trader.id, stock_symbol=sym, quantity=qty, average_buy_price=price, allocation_percentage=25.0))
            for sym in ["AAPL", "TSLA", "NVDA", "AMZN", "GOOGL"]:
                db.add(Watchlist(user_id=trader.id, stock_symbol=sym))
            print("[OK] Demo trader created: demo@trademind.ai / Demo@123")

        await db.commit()
        print("[OK] Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
