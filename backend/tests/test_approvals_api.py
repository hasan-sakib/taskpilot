from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.runner import run_graph
from app.agent.graph.state import build_initial_state
from app.agent.llm.base import PlanResponse, PlanTaskSpec
from app.agent.llm.test_provider import ScriptedTestProvider
from app.agent.tools.registry import build_default_registry
from app.db.base import utcnow
from app.db.models.agent_run import AgentRun
from app.db.models.approval_request import ApprovalRequest
from app.db.models.enums import RunStatus


async def _seed_paused_run_with_approval(
    session_factory, api_settings, *, run_id="run-1", expires_in=timedelta(minutes=15)
) -> str:
    """Actually runs the graph to a real paused-for-approval state (a real LangGraph
    checkpoint, not just fabricated DB rows) -- resolve_approval's resume_graph call
    needs a genuine checkpoint to resume from; a hand-inserted ApprovalRequest row with
    no matching checkpoint fails with a KeyError deep in the resumed node instead of
    exercising the real approve/reject path."""
    workspace_root = str(api_settings.resolved_workspace_root())
    async with session_factory() as session:
        session.add(
            AgentRun(
                id=run_id,
                goal="Write a file",
                status=RunStatus.PENDING,
                workspace_root=workspace_root,
                test_mode=True,
            )
        )
        await session.commit()

    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="Write a.txt",
                        tool_name="workspace.write_file",
                        tool_args={"path": "a.txt", "content": "hi"},
                    )
                ]
            )
        ],
        report="Wrote the file.",
    )
    deps = GraphDependencies(
        llm_provider=provider,
        tool_registry=build_default_registry(),
        settings=api_settings,
        session_factory=session_factory,
    )
    initial_state = build_initial_state(
        run_id=run_id, goal="Write a file", workspace_root=workspace_root, llm_provider="test"
    )
    await run_graph(run_id, initial_state, deps)

    async with session_factory() as session:
        approval = (
            await session.scalars(select(ApprovalRequest).where(ApprovalRequest.run_id == run_id))
        ).first()
        approval_id = approval.id
        if expires_in != timedelta(minutes=15):
            row = await session.get(ApprovalRequest, approval_id)
            row.expires_at = utcnow() + expires_in
            await session.commit()

    return approval_id


@pytest.mark.asyncio
async def test_list_approvals_returns_pending(
    api_client: AsyncClient, api_session_factory, api_settings
):
    await _seed_paused_run_with_approval(api_session_factory, api_settings)

    resp = await api_client.get("/api/v1/approvals")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "pending"
    assert body[0]["action_type"] == "workspace.write_file"
    assert body[0]["action_payload"] == {"path": "a.txt", "content": "hi"}


@pytest.mark.asyncio
async def test_list_approvals_filters_by_status(
    api_client: AsyncClient, api_session_factory, api_settings
):
    await _seed_paused_run_with_approval(api_session_factory, api_settings)

    resp = await api_client.get("/api/v1/approvals", params={"status": "approved"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_approval_404(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/approvals/missing")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_approval_returns_detail(
    api_client: AsyncClient, api_session_factory, api_settings
):
    approval_id = await _seed_paused_run_with_approval(api_session_factory, api_settings)

    resp = await api_client.get(f"/api/v1/approvals/{approval_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == approval_id


@pytest.mark.asyncio
async def test_approve_404_for_unknown_id(api_client: AsyncClient):
    resp = await api_client.post("/api/v1/approvals/missing/approve")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_runs_the_tool_and_completes_the_run(
    api_client: AsyncClient, api_session_factory, api_settings
):
    approval_id = await _seed_paused_run_with_approval(
        api_session_factory, api_settings, run_id="run-approve"
    )

    resp = await api_client.post(
        f"/api/v1/approvals/{approval_id}/approve", json={"resolved_by": "tester"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["resolved_by"] == "tester"

    run_resp = await api_client.get("/api/v1/agent/runs/run-approve")
    assert run_resp.json()["status"] == "completed"
    assert (api_settings.resolved_workspace_root() / "a.txt").read_text() == "hi"


@pytest.mark.asyncio
async def test_reject_marks_task_failed_without_running_tool(
    api_client: AsyncClient, api_session_factory, api_settings
):
    approval_id = await _seed_paused_run_with_approval(
        api_session_factory, api_settings, run_id="run-reject"
    )

    resp = await api_client.post(
        f"/api/v1/approvals/{approval_id}/reject",
        json={"rejection_reason": "not needed"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "not needed"
    assert not (api_settings.resolved_workspace_root() / "a.txt").exists()


@pytest.mark.asyncio
async def test_approve_already_resolved_returns_409(
    api_client: AsyncClient, api_session_factory, api_settings
):
    approval_id = await _seed_paused_run_with_approval(
        api_session_factory, api_settings, run_id="run-double"
    )

    first = await api_client.post(f"/api/v1/approvals/{approval_id}/reject")
    assert first.status_code == 200

    second = await api_client.post(f"/api/v1/approvals/{approval_id}/approve")
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_approve_expired_returns_409(
    api_client: AsyncClient, api_session_factory, api_settings
):
    approval_id = await _seed_paused_run_with_approval(
        api_session_factory,
        api_settings,
        run_id="run-expired",
        expires_in=timedelta(seconds=-1),
    )

    resp = await api_client.post(f"/api/v1/approvals/{approval_id}/approve")
    assert resp.status_code == 409

    get_resp = await api_client.get(f"/api/v1/approvals/{approval_id}")
    assert get_resp.json()["status"] == "expired"


@pytest.mark.asyncio
async def test_expired_approval_is_swept_on_list(
    api_client: AsyncClient, api_session_factory, api_settings
):
    await _seed_paused_run_with_approval(
        api_session_factory, api_settings, run_id="run-sweep", expires_in=timedelta(seconds=-1)
    )

    resp = await api_client.get("/api/v1/approvals", params={"status": "pending"})
    assert resp.json() == []

    resp_all = await api_client.get("/api/v1/approvals")
    assert resp_all.json()[0]["status"] == "expired"
