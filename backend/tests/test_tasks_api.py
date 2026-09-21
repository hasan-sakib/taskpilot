import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.runner import run_graph
from app.agent.graph.state import build_initial_state
from app.agent.llm.base import PlanResponse, PlanTaskSpec
from app.agent.llm.test_provider import ScriptedTestProvider
from app.agent.tools.registry import build_default_registry
from app.core.config import Settings
from app.db.models.agent_run import AgentRun
from app.db.models.enums import RunStatus


async def _run_a_completed_task(
    api_session_factory: async_sessionmaker, api_settings: Settings, run_id: str
) -> None:
    """Seeds a real AgentRun with one AUTO-permission task (no approval needed) through
    the actual graph, against the same DB api_client is wired to -- an empty-plan run
    (the pattern the other route tests use) never produces a task row at all, which
    isn't useful for testing an endpoint whose whole job is listing tasks."""
    async with api_session_factory() as session:
        session.add(
            AgentRun(
                id=run_id,
                goal="List the workspace",
                status=RunStatus.PENDING,
                workspace_root=str(api_settings.resolved_workspace_root()),
                test_mode=True,
            )
        )
        await session.commit()

    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="List the workspace root",
                        tool_name="workspace.list_dir",
                        tool_args={"path": "."},
                    )
                ]
            )
        ],
        report="Listed the workspace.",
    )
    deps = GraphDependencies(
        llm_provider=provider,
        tool_registry=build_default_registry(),
        settings=api_settings,
        session_factory=api_session_factory,
    )
    initial_state = build_initial_state(
        run_id=run_id,
        goal="List the workspace",
        workspace_root=str(api_settings.resolved_workspace_root()),
        llm_provider="test",
    )
    await run_graph(run_id, initial_state, deps)


@pytest.mark.asyncio
async def test_list_tasks_empty(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_tasks_after_a_run_includes_its_tasks(
    api_client: AsyncClient, api_session_factory, api_settings
):
    await _run_a_completed_task(api_session_factory, api_settings, "run-with-task")

    resp = await api_client.get("/api/v1/tasks", params={"run_id": "run-with-task"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["run_id"] == "run-with-task"
    assert body[0]["tool_name"] == "workspace.list_dir"
    assert body[0]["status"] == "completed"
    assert body[0]["dependencies"] == []


@pytest.mark.asyncio
async def test_list_tasks_filters_by_run_id(
    api_client: AsyncClient, api_session_factory, api_settings
):
    await _run_a_completed_task(api_session_factory, api_settings, "run-a")
    await _run_a_completed_task(api_session_factory, api_settings, "run-b")

    resp = await api_client.get("/api/v1/tasks", params={"run_id": "run-a"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["run_id"] == "run-a"


@pytest.mark.asyncio
async def test_list_tasks_filters_by_status(
    api_client: AsyncClient, api_session_factory, api_settings
):
    await _run_a_completed_task(api_session_factory, api_settings, "run-c")

    completed = await api_client.get("/api/v1/tasks", params={"status": "completed"})
    assert len(completed.json()) == 1

    failed = await api_client.get("/api/v1/tasks", params={"status": "failed"})
    assert failed.json() == []


@pytest.mark.asyncio
async def test_list_tasks_rejects_invalid_status(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/tasks", params={"status": "not-a-status"})
    assert resp.status_code == 422
