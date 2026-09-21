from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_session  # also registers all models onto Base.metadata
from app.db.sqlite_pragma import configure_sqlite_connection


@pytest_asyncio.fixture
async def api_client(tmp_path: Path, monkeypatch) -> AsyncIterator[AsyncClient]:
    """Wires the FastAPI app, the graph's default session_factory (via a monkeypatched
    global SessionLocal), and Settings all to the same isolated in-memory DB + tmp
    workspace -- so a real POST /agent/runs exercises the full route -> graph -> DB path
    without touching the real dev database or a real LLM."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    configure_sqlite_connection(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    import app.db.session as db_session_module

    monkeypatch.setattr(db_session_module, "SessionLocal", session_factory)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    test_settings = Settings(data_dir=tmp_path / "data", workspace_root=workspace_root)

    from app.main import app

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_settings] = lambda: test_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_run_executes_synchronously_end_to_end(api_client: AsyncClient):
    resp = await api_client.post(
        "/api/v1/agent/runs", json={"goal": "List workspace files", "llm_provider": "test"}
    )
    assert resp.status_code == 201
    body = resp.json()
    # The route's default "test" provider has no scripted plan, so the run predictably
    # fails plan validation -- what this test actually verifies is that the route wired
    # the graph, DB, and settings together correctly end-to-end and persisted the result,
    # not planning correctness (that's covered by the agent test suite).
    assert body["status"] == "failed"
    assert body["final_report"] is not None
    run_id = body["id"]

    get_resp = await api_client.get(f"/api/v1/agent/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == run_id
    assert get_resp.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_get_run_404_for_unknown_id(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/agent/runs/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_run_rejects_empty_goal(api_client: AsyncClient):
    resp = await api_client.post("/api/v1/agent/runs", json={"goal": "", "llm_provider": "test"})
    assert resp.status_code == 422
