from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.sqlite_pragma import enable_sqlite_foreign_keys

settings = get_settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.app_db_url, echo=False)
enable_sqlite_foreign_keys(engine)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
