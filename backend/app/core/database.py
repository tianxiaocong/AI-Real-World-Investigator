from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.models.entities import Base

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"timeout": 30}

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    future=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def init_db():
    """Initialize database tables and auto-migrate missing columns"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        def _migrate(sync_conn):
            from sqlalchemy import text
            try:
                sync_conn.execute(text("ALTER TABLE claims ADD COLUMN metadata JSON DEFAULT '{}'"))
            except Exception:
                pass
            try:
                sync_conn.execute(text("ALTER TABLE sources ADD COLUMN raw_text TEXT"))
            except Exception:
                pass
        await conn.run_sync(_migrate)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining DB session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
