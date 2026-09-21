import pytest
from pydantic import BaseModel
from sqlalchemy import select

from app.agent.graph.runner import run_graph
from app.agent.llm.base import PlanResponse, PlanTaskSpec
from app.agent.llm.test_provider import ScriptedTestProvider
from app.agent.nodes.retry_recovery import make as make_retry_recovery_node
from app.agent.policies.approval_policy import compute_payload_hash
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.agent.tools.registry import ToolRegistry
from app.agent.tools.task_management.retry_task import RetryTaskInput, RetryTaskTool
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.enums import RunStatus, TaskStatus, ToolExecutionStatus
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


@pytest.mark.asyncio
async def test_automatic_retries_never_roll_back_a_prior_manual_retry_count(
    agent_session_factory, make_deps, workspace_root
):
    """Regression test for a deadlock bug: retry_recovery used to ASSIGN
    task.retry_count from graph-state retry_count (which resets to 0 every attempt
    sequence) instead of incrementing the DB value. That let an automatic retry
    sequence silently roll task.retry_count back down after a manual task.retry call
    had already pushed it higher -- so a second manual retry could recompute the exact
    same retry_count (and therefore the same approval payload_hash) as an earlier
    attempt, collide with that attempt's already-resolved ApprovalRequest, and deadlock
    the run waiting on an approval nothing could ever resolve again. task.retry_count
    must be strictly increasing across the task's whole lifetime, whichever of the two
    writers (automatic retry_recovery, manual task.retry) touches it.
    """
    run_id = "run-retry-count-monotonic"
    async with agent_session_factory() as session:
        session.add(
            AgentRun(
                id=run_id,
                goal="g",
                status=RunStatus.RUNNING,
                workspace_root=str(workspace_root),
            )
        )
        task = AgentTask(
            run_id=run_id,
            plan_version=1,
            sequence_index=0,
            description="d",
            tool_name="test.always_fails",
            tool_args={},
            status=TaskStatus.FAILED,
            retry_count=3,  # as if 3 automatic retries already happened
        )
        session.add(task)
        await session.commit()
        task_id = task.id

    deps = make_deps(ScriptedTestProvider())
    tool_ctx = ToolRunContext(
        workspace_root=workspace_root,
        run_id=run_id,
        task_id=task_id,
        execution_id="e1",
        session_factory=deps.session_factory,
        tool_registry=deps.tool_registry,
        llm_provider=deps.llm_provider,
        settings=deps.settings,
    )

    first_retry = await RetryTaskTool().run(RetryTaskInput(task_id=task_id), tool_ctx)
    assert first_retry.retry_count == 4

    # Simulate a fresh automatic-retry sequence on this new manual attempt: graph-state
    # retry_count starts at 0 again (as replanning/result_verification would leave it),
    # running through retry_recovery directly (it makes no interrupt() call, so it's
    # safe to invoke outside a live graph).
    retry_recovery_node = make_retry_recovery_node(deps)
    state = {
        "run_id": run_id,
        "current_task_id": task_id,
        "retry_count": 0,
        "max_retries_per_task": 3,
        "approval_decision": None,
    }
    for _ in range(4):  # 3 retries, then the exhausting 4th call
        out = await retry_recovery_node(state)
        state["retry_count"] = out["retry_count"]
    assert out["retry_recovery_outcome"] == "exhausted"

    async with agent_session_factory() as session:
        task = await session.get(AgentTask, task_id)
        assert task.retry_count == 8  # 4 (manual) + 4 more increments -- never rolled back
        assert task.status == TaskStatus.FAILED

    second_retry = await RetryTaskTool().run(RetryTaskInput(task_id=task_id), tool_ctx)
    assert second_retry.retry_count == 9
    assert second_retry.retry_count != first_retry.retry_count

    # The actual load-bearing invariant: the two attempts must produce different
    # approval payload hashes, so the second manual retry gets its own resolvable
    # ApprovalRequest instead of colliding with the first attempt's already-resolved one.
    hash_kwargs = {
        "tool_name": "test.always_fails",
        "args": {},
        "target": None,
        "run_id": run_id,
        "task_id": task_id,
        "workspace_root": str(workspace_root),
    }
    hash_at_first_retry = compute_payload_hash(**hash_kwargs, retry_count=first_retry.retry_count)
    hash_at_second_retry = compute_payload_hash(**hash_kwargs, retry_count=second_retry.retry_count)
    assert hash_at_first_retry != hash_at_second_retry
