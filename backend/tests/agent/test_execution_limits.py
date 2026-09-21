import pytest

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.runner import run_graph
from app.agent.llm.base import PlanResponse, PlanTaskSpec
from app.agent.llm.test_provider import ScriptedTestProvider
from app.agent.tools.registry import build_default_registry
from app.core.config import Settings
from app.db.models.agent_run import AgentRun
from app.db.models.enums import RunStatus
from tests.agent.helpers import create_run


@pytest.mark.asyncio
async def test_tool_call_limit_exceeded_sets_failed_status_with_reason(
    agent_session_factory, agent_settings: Settings, workspace_root
):
    # A run whose plan needs more tool calls than the configured budget must stop and
    # report FAILED with a reason -- not silently masquerade as COMPLETED just because
    # the tasks that did run happened to succeed.
    agent_settings.max_tool_calls_per_run = 0

    initial_state = await create_run(
        agent_session_factory,
        run_id="run-limit",
        goal="List files",
        workspace_root=str(workspace_root),
    )
    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="List root",
                        tool_name="workspace.list_dir",
                        tool_args={"path": "."},
                    )
                ]
            )
        ],
        report="n/a",
    )
    deps = GraphDependencies(
        llm_provider=provider,
        tool_registry=build_default_registry(),
        settings=agent_settings,
        session_factory=agent_session_factory,
    )

    result = await run_graph("run-limit", initial_state, deps)

    assert result["status"] == RunStatus.FAILED

    async with agent_session_factory() as session:
        run = await session.get(AgentRun, "run-limit")
        assert run.status == RunStatus.FAILED
        assert "max_tool_calls_per_run" in run.error_message


@pytest.mark.asyncio
async def test_cancelled_run_reports_cancelled_status(
    agent_session_factory, make_deps, workspace_root
):
    initial_state = await create_run(
        agent_session_factory,
        run_id="run-cancel",
        goal="List files",
        workspace_root=str(workspace_root),
    )
    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="List root",
                        tool_name="workspace.list_dir",
                        tool_args={"path": "."},
                    )
                ]
            )
        ],
        report="n/a",
    )
    deps = make_deps(provider)

    async with agent_session_factory() as session:
        run = await session.get(AgentRun, "run-cancel")
        run.cancel_requested = True
        await session.commit()

    result = await run_graph("run-cancel", initial_state, deps)

    assert result["status"] == RunStatus.CANCELLED

    async with agent_session_factory() as session:
        run = await session.get(AgentRun, "run-cancel")
        assert run.status == RunStatus.CANCELLED
        assert run.error_message == "Run was cancelled"
