from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# Importing this subpackage is what registers every model onto Base.metadata (each
# model module's class body runs as a side effect of being imported). Anything that
# creates tables from Base.metadata -- Alembic env.py, and every test fixture that does
# Base.metadata.create_all on an in-memory DB -- depends on this having already
# happened. Doing it here, in the module every DB access path imports, means it's
# never left to accidental import order elsewhere (which is exactly how this bug
# first surfaced: a fixture's create_all() silently created zero tables because no
# model module had been imported yet in that process).
from app.db import models as _models  # noqa: F401
from app.db.sqlite_pragma import configure_sqlite_connection

settings = get_settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.app_db_url, echo=False)
configure_sqlite_connection(engine)
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
