from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Explicitly imported here (not just relied on transitively via app.db.session below) so
# this fixture's Base.metadata.create_all() can never silently create zero tables --
# see app/db/session.py for the full story on why that's a real failure mode.
from app.core.config import Settings, get_settings
from app.db import models as _models  # noqa: F401
from app.db.base import Base
from app.db.session import get_session
from app.db.sqlite_pragma import configure_sqlite_connection


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    configure_sqlite_connection(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    from app.main import app

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_session_factory(
    monkeypatch,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A session_factory usable both to seed rows directly in a test and as the
    backing store for a live api_client -- shared by any test exercising a full
    route -> service -> DB path (e.g. approvals resolve, agent run creation)."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    configure_sqlite_connection(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    # GraphDependencies' default session_factory does a lazy `from app.db.session
    # import SessionLocal` at call time (see app/agent/graph/deps.py), so patching the
    # module attribute here is picked up by any code that builds GraphDependencies
    # without an explicit session_factory -- e.g. the approvals route resolving a run.
    import app.db.session as db_session_module

    monkeypatch.setattr(db_session_module, "SessionLocal", session_factory)

    yield session_factory
    await engine.dispose()


@pytest.fixture
def api_settings(tmp_path: Path) -> Settings:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    return Settings(data_dir=tmp_path / "data", workspace_root=workspace_root)


@pytest_asyncio.fixture
async def api_client(
    api_session_factory: async_sessionmaker[AsyncSession], api_settings: Settings
) -> AsyncIterator[AsyncClient]:
    """Wires the FastAPI app, the graph's default session_factory, and Settings all to
    the same isolated in-memory DB + tmp workspace -- so a real HTTP request exercises
    the full route -> graph/service -> DB path without touching the real dev database
    or a real LLM."""
    from app.main import app

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        async with api_session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_settings] = lambda: api_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
