import pytest
from httpx import AsyncClient

from app.db.base import utcnow
from app.db.models.agent_run import AgentRun
from app.db.models.browser_session import BrowserSession
from app.db.models.enums import BrowserSessionStatus, RunStatus


async def _seed_browser_session(api_session_factory, api_settings, *, run_id, session_id) -> None:
    async with api_session_factory() as session:
        session.add(
            AgentRun(
                id=run_id,
                goal="Browse something",
                status=RunStatus.RUNNING,
                workspace_root=str(api_settings.resolved_workspace_root()),
                test_mode=True,
            )
        )
        session.add(
            BrowserSession(
                id=session_id,
                run_id=run_id,
                status=BrowserSessionStatus.CLOSED,
                current_url="https://example.com",
                headless=True,
                started_at=utcnow(),
                closed_at=utcnow(),
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_list_browser_sessions_empty(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/browser/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_browser_sessions_returns_seeded_session(
    api_client: AsyncClient, api_session_factory, api_settings
):
    await _seed_browser_session(
        api_session_factory, api_settings, run_id="run-1", session_id="session-1"
    )

    resp = await api_client.get("/api/v1/browser/sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == "session-1"
    assert body[0]["current_url"] == "https://example.com"
    assert body[0]["status"] == "closed"
    # Never started via the real BrowserSessionManager in this test -- must not be
    # reported as live just because a DB row exists.
    assert body[0]["is_live"] is False


@pytest.mark.asyncio
async def test_list_browser_sessions_filters_by_run_id(
    api_client: AsyncClient, api_session_factory, api_settings
):
    await _seed_browser_session(
        api_session_factory, api_settings, run_id="run-a", session_id="session-a"
    )
    await _seed_browser_session(
        api_session_factory, api_settings, run_id="run-b", session_id="session-b"
    )

    resp = await api_client.get("/api/v1/browser/sessions", params={"run_id": "run-a"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["run_id"] == "run-a"
