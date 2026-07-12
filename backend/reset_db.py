"""
Drops all tables and recreates them fresh, then seeds only the admin account.
Run from the backend directory:
  python reset_db.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base
from app.models.models import User, PaperTrading
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"ssl": "require"} if settings.DATABASE_URL.startswith("postgresql") else {},
)
Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def reset():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("[OK] All tables dropped.")
        await conn.run_sync(Base.metadata.create_all)
        print("[OK] All tables recreated.")

    async with Session() as db:
        if not settings.ADMIN_PASSWORD_HASH:
            raise RuntimeError(
                "ADMIN_PASSWORD_HASH is not set in .env\n"
                "Generate it with:\n"
                "  python -c \"from app.core.security import hash_password; print(hash_password('YourPassword'))\""
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
        await db.commit()
        print(f"[OK] Admin seeded: {settings.ADMIN_EMAIL}")
        print("[DONE] Database reset complete. Fresh for new users.")


if __name__ == "__main__":
    asyncio.run(reset())
