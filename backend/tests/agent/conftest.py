from collections.abc import AsyncIterator, Callable
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agent.graph.deps import GraphDependencies
from app.agent.llm.base import LLMProvider
from app.agent.tools.registry import ToolRegistry, build_default_registry
from app.core.config import Settings

# Must be imported before Base.metadata.create_all() below -- it's what registers every
# model onto Base.metadata as a side effect. Without it, create_all() silently creates
# zero tables if nothing else in the process happened to import the models package first.
from app.db import models as _models  # noqa: F401,E402
from app.db.base import Base
from app.db.sqlite_pragma import configure_sqlite_connection


@pytest_asyncio.fixture
async def agent_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    configure_sqlite_connection(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    yield session_factory
    await engine.dispose()


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    return root


@pytest.fixture
def agent_settings(tmp_path: Path, workspace_root: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", workspace_root=workspace_root)


@pytest.fixture
def make_deps(
    agent_settings: Settings,
    agent_session_factory: async_sessionmaker[AsyncSession],
) -> Callable[..., GraphDependencies]:
    def _make(
        llm_provider: LLMProvider, tool_registry: ToolRegistry | None = None
    ) -> GraphDependencies:
        return GraphDependencies(
            llm_provider=llm_provider,
            tool_registry=tool_registry or build_default_registry(),
            settings=agent_settings,
            session_factory=agent_session_factory,
        )

    return _make
