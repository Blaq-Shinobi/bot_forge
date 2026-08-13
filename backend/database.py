"""Async SQLAlchemy database setup."""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import get_settings
settings = get_settings()
engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
class Base(DeclarativeBase):
    pass
async def get_db() -> AsyncSession:
    """Dependency: yields an async DB session."""
    async with async_session() as session:
        yield session
async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
