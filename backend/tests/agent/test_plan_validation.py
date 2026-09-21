import pytest
from sqlalchemy import select

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.runner import run_graph
from app.agent.graph.state import PlanTask
from app.agent.llm.base import PlanResponse, PlanTaskSpec
from app.agent.llm.test_provider import ScriptedTestProvider
from app.agent.nodes.plan_validation import _has_cycle, _validate_plan
from app.db.models.agent_event import AgentEvent
from app.db.models.enums import RunStatus
from tests.agent.helpers import create_run


def _task(
    task_id: str, tool_name: str = "workspace.list_dir", depends_on: list[str] | None = None
) -> PlanTask:
    return PlanTask(
        task_id=task_id,
        sequence_index=0,
        description="d",
        tool_name=tool_name,
        tool_args={"path": "."},
        depends_on=depends_on or [],
    )


def test_has_cycle_detects_self_and_mutual_cycles():
    assert _has_cycle([_task("a", depends_on=["a"])]) is True
    assert _has_cycle([_task("a", depends_on=["b"]), _task("b", depends_on=["a"])]) is True
    assert _has_cycle([_task("a", depends_on=["b"]), _task("b")]) is False
    assert _has_cycle([]) is False


def test_validate_plan_rejects_empty_plan(make_deps):
    deps: GraphDependencies = make_deps(ScriptedTestProvider())
    errors = _validate_plan([], deps)
    assert errors == ["Plan has no tasks"]


def test_validate_plan_rejects_unknown_tool(make_deps):
    deps: GraphDependencies = make_deps(ScriptedTestProvider())
    errors = _validate_plan([_task("a", tool_name="not_a_real_tool")], deps)
    assert any("Unknown tool" in e for e in errors)


def test_validate_plan_rejects_bad_args(make_deps):
    deps: GraphDependencies = make_deps(ScriptedTestProvider())
    bad_task = PlanTask(
        task_id="a",
        sequence_index=0,
        description="d",
        tool_name="workspace.write_file",
        tool_args={"path": "x.txt"},  # missing required "content"
    )
    errors = _validate_plan([bad_task], deps)
    assert any("Invalid args" in e for e in errors)


def test_validate_plan_rejects_dangling_dependency(make_deps):
    deps: GraphDependencies = make_deps(ScriptedTestProvider())
    errors = _validate_plan([_task("a", depends_on=["missing"])], deps)
    assert any("depends on unknown task" in e for e in errors)


def test_validate_plan_accepts_well_formed_plan(make_deps):
    deps: GraphDependencies = make_deps(ScriptedTestProvider())
    errors = _validate_plan([_task("a"), _task("b", depends_on=["a"])], deps)
    assert errors == []


@pytest.mark.asyncio
async def test_repeatedly_invalid_plan_exhausts_attempts_and_fails_run(
    agent_session_factory, make_deps, workspace_root
):
    initial_state = await create_run(
        agent_session_factory,
        run_id="run-bad-plan",
        goal="Do something",
        workspace_root=str(workspace_root),
    )
    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="Use a tool that doesn't exist",
                        tool_name="not_a_real_tool",
                        tool_args={},
                    )
                ]
            )
        ],
        report="n/a",
    )
    deps = make_deps(provider)

    result = await run_graph("run-bad-plan", initial_state, deps)

    assert result["status"] == RunStatus.FAILED
    # planning is retried up to max_plan_validation_attempts (default 3) before giving up.
    assert len(provider.plan_requests) == 3

    async with agent_session_factory() as session:
        invalid_events = list(
            await session.scalars(
                select(AgentEvent).where(
                    AgentEvent.run_id == "run-bad-plan", AgentEvent.event_type == "plan_invalid"
                )
            )
        )
        assert len(invalid_events) == 3
