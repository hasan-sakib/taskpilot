import pytest
from sqlalchemy import select

from app.agent.graph.runner import run_graph
from app.agent.llm.base import PlanResponse, PlanTaskSpec
from app.agent.llm.test_provider import ScriptedTestProvider
from app.db.models.agent_event import AgentEvent
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.enums import RunStatus, TaskStatus
from tests.agent.helpers import create_run


@pytest.mark.asyncio
async def test_happy_path_run_completes_deterministically(
    agent_session_factory, make_deps, workspace_root
):
    (workspace_root / "notes.txt").write_text("hello")

    initial_state = await create_run(
        agent_session_factory,
        run_id="run-1",
        goal="List workspace files",
        workspace_root=str(workspace_root),
    )
    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="List workspace root",
                        tool_name="workspace.list_dir",
                        tool_args={"path": "."},
                    )
                ]
            )
        ],
        report="Listed the workspace successfully.",
    )
    deps = make_deps(provider)

    result = await run_graph("run-1", initial_state, deps)

    assert "__interrupt__" not in result
    assert result["status"] == RunStatus.COMPLETED
    assert result["final_report"] == "Listed the workspace successfully."

    async with agent_session_factory() as session:
        run = await session.get(AgentRun, "run-1")
        assert run.status == RunStatus.COMPLETED
        assert run.final_report == "Listed the workspace successfully."
        assert run.plan_version == 1

        events = list(
            await session.scalars(
                select(AgentEvent)
                .where(AgentEvent.run_id == "run-1")
                .order_by(AgentEvent.created_at)
            )
        )
        event_types = [e.event_type for e in events]

        # Confirms the graph actually walked goal -> plan -> validate -> select ->
        # permission -> observe -> verify -> select(done) -> complete -> report, not
        # just that the end state happens to look right.
        assert event_types == [
            "goal_validated",
            "plan_generated",
            "plan_validated",
            "task_selected",
            "permission_auto_approved",
            "tool_result_observed",
            "task_completed",
            "all_tasks_done",
            "completion_done",
            "final_report_generated",
        ]

        # Zero network/model calls: the only "model" involved is our in-process script.
        assert len(provider.plan_requests) == 1
        assert len(provider.report_requests) == 1


@pytest.mark.asyncio
async def test_invalid_goal_short_circuits_to_final_report(
    agent_session_factory, make_deps, workspace_root
):
    initial_state = await create_run(
        agent_session_factory,
        run_id="run-invalid-goal",
        goal="   ",
        workspace_root=str(workspace_root),
    )
    deps = make_deps(ScriptedTestProvider())

    result = await run_graph("run-invalid-goal", initial_state, deps)

    assert result["status"] == RunStatus.FAILED
    assert result["clarification_needed"] is True
    assert "could not be validated" in result["final_report"]

    async with agent_session_factory() as session:
        events = list(
            await session.scalars(
                select(AgentEvent)
                .where(AgentEvent.run_id == "run-invalid-goal")
                .order_by(AgentEvent.created_at)
            )
        )
        # Never reaches planning at all.
        assert [e.event_type for e in events] == ["goal_invalid", "final_report_generated"]


@pytest.mark.asyncio
async def test_multi_task_plan_respects_dependencies(
    agent_session_factory, make_deps, workspace_root
):
    initial_state = await create_run(
        agent_session_factory,
        run_id="run-deps",
        goal="Two step plan",
        workspace_root=str(workspace_root),
    )
    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="First: list root",
                        tool_name="workspace.list_dir",
                        tool_args={"path": "."},
                        depends_on=[],
                    ),
                    PlanTaskSpec(
                        description="Second: list root again, depends on first",
                        tool_name="workspace.list_dir",
                        tool_args={"path": "."},
                        depends_on=[0],
                    ),
                ]
            )
        ],
        report="Both steps completed.",
    )
    deps = make_deps(provider)

    result = await run_graph("run-deps", initial_state, deps)

    assert result["status"] == RunStatus.COMPLETED
    async with agent_session_factory() as session:
        events = list(
            await session.scalars(
                select(AgentEvent)
                .where(AgentEvent.run_id == "run-deps", AgentEvent.event_type == "task_selected")
                .order_by(AgentEvent.created_at)
            )
        )
        # task_selected must fire twice, in dependency order (task 0 before task 1).
        assert len(events) == 2

        first_task = await session.get(AgentTask, events[0].task_id)
        second_task = await session.get(AgentTask, events[1].task_id)
        assert first_task.sequence_index == 0
        assert second_task.sequence_index == 1
        assert first_task.status == TaskStatus.COMPLETED
        assert second_task.status == TaskStatus.COMPLETED
