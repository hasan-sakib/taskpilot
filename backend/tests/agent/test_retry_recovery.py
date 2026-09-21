import pytest
from pydantic import BaseModel
from sqlalchemy import select

from app.agent.graph.runner import run_graph
from app.agent.llm.base import PlanResponse, PlanTaskSpec
from app.agent.llm.test_provider import ScriptedTestProvider
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.agent.tools.registry import ToolRegistry
from app.db.models.enums import RunStatus, ToolExecutionStatus
from app.db.models.tool_execution import ToolExecution
from tests.agent.helpers import create_run


class _EmptyInput(BaseModel):
    pass


class _EmptyOutput(BaseModel):
    ok: bool = True


class _FailNTimesTool(Tool):
    """Test-only tool: fails its first `fail_count` calls, then succeeds."""

    name = "test.fail_n_times"
    category = ToolCategory.WORKSPACE
    description = "Fails a configured number of times, then succeeds."
    input_schema = _EmptyInput
    output_schema = _EmptyOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 5

    def __init__(self, fail_count: int) -> None:
        self.fail_count = fail_count
        self.calls = 0

    async def run(self, args: _EmptyInput, ctx: ToolRunContext) -> _EmptyOutput:
        self.calls += 1
        if self.calls <= self.fail_count:
            raise ToolError(f"simulated failure #{self.calls}")
        return _EmptyOutput()


class _AlwaysFailsTool(Tool):
    name = "test.always_fails"
    category = ToolCategory.WORKSPACE
    description = "Always fails."
    input_schema = _EmptyInput
    output_schema = _EmptyOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 5

    def __init__(self) -> None:
        self.calls = 0

    async def run(self, args: _EmptyInput, ctx: ToolRunContext) -> _EmptyOutput:
        self.calls += 1
        raise ToolError("this tool never succeeds")


@pytest.mark.asyncio
async def test_transient_failure_retries_then_succeeds(
    agent_session_factory, make_deps, workspace_root
):
    tool = _FailNTimesTool(fail_count=2)
    registry = ToolRegistry()
    registry.register(tool)

    initial_state = await create_run(
        agent_session_factory,
        run_id="run-retry-ok",
        goal="Retry then succeed",
        workspace_root=str(workspace_root),
    )
    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(tasks=[PlanTaskSpec(description="d", tool_name=tool.name, tool_args={})])
        ],
        report="Eventually succeeded.",
    )
    deps = make_deps(provider, registry)

    result = await run_graph("run-retry-ok", initial_state, deps)

    assert result["status"] == RunStatus.COMPLETED
    assert tool.calls == 3  # 2 failures + 1 success

    async with agent_session_factory() as session:
        executions = list(
            await session.scalars(
                select(ToolExecution)
                .where(ToolExecution.run_id == "run-retry-ok")
                .order_by(ToolExecution.attempt_number)
            )
        )
        assert [e.attempt_number for e in executions] == [1, 2, 3]
        assert [e.status for e in executions] == [
            ToolExecutionStatus.FAILED,
            ToolExecutionStatus.FAILED,
            ToolExecutionStatus.SUCCEEDED,
        ]


@pytest.mark.asyncio
async def test_failure_exhausts_retries_then_replans_and_fails(
    agent_session_factory, make_deps, workspace_root
):
    tool = _AlwaysFailsTool()
    registry = ToolRegistry()
    registry.register(tool)

    initial_state = await create_run(
        agent_session_factory,
        run_id="run-retry-exhausted",
        goal="Always fails",
        workspace_root=str(workspace_root),
    )
    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(tasks=[PlanTaskSpec(description="d", tool_name=tool.name, tool_args={})])
        ],
        report="Gave up.",
    )
    deps = make_deps(provider, registry)

    result = await run_graph("run-retry-exhausted", initial_state, deps)

    assert result["status"] == RunStatus.FAILED
    # 1 initial attempt + max_retries_per_task (default 3) retries = 4 calls, then
    # retry_recovery gives up and replanning proposes the same broken plan again,
    # repeating until max_replanning_attempts (default 3) is exhausted.
    max_retries = deps.settings.max_retries_per_task
    max_replanning = deps.settings.max_replanning_attempts
    assert tool.calls == (max_retries + 1) * (max_replanning + 1)

    async with agent_session_factory() as session:
        executions = list(
            await session.scalars(
                select(ToolExecution).where(ToolExecution.run_id == "run-retry-exhausted")
            )
        )
        assert all(e.status == ToolExecutionStatus.FAILED for e in executions)
