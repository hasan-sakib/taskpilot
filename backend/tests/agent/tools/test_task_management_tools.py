import pytest

from app.agent.tools.base import ToolError
from app.agent.tools.task_management.add_dependency import AddDependencyInput, AddDependencyTool
from app.agent.tools.task_management.cancel_task import CancelTaskInput, CancelTaskTool
from app.agent.tools.task_management.create_task import CreateTaskInput, CreateTaskTool
from app.agent.tools.task_management.get_task import GetTaskInput, GetTaskTool
from app.agent.tools.task_management.list_tasks import ListTasksInput, ListTasksTool
from app.agent.tools.task_management.record_result import RecordResultInput, RecordResultTool
from app.agent.tools.task_management.retry_task import RetryTaskInput, RetryTaskTool
from app.agent.tools.task_management.set_priority_deadline import (
    SetPriorityDeadlineInput,
    SetPriorityDeadlineTool,
)
from app.agent.tools.task_management.update_status import UpdateStatusInput, UpdateStatusTool
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.enums import RunStatus, TaskStatus


async def _seed_run(session_factory, run_id: str = "test-run", *, plan_version: int = 1) -> None:
    async with session_factory() as session:
        if await session.get(AgentRun, run_id) is None:
            session.add(
                AgentRun(
                    id=run_id,
                    goal="g",
                    status=RunStatus.RUNNING,
                    workspace_root="/w",
                    plan_version=plan_version,
                )
            )
            await session.commit()


async def _seed_task(
    session_factory,
    run_id: str = "test-run",
    *,
    plan_version: int = 1,
    sequence_index: int = 0,
    status: TaskStatus = TaskStatus.PENDING,
    tool_name: str = "workspace.list_dir",
    tool_args: dict | None = None,
) -> str:
    await _seed_run(session_factory, run_id)
    async with session_factory() as session:
        task = AgentTask(
            run_id=run_id,
            plan_version=plan_version,
            sequence_index=sequence_index,
            description="d",
            tool_name=tool_name,
            tool_args=tool_args or {"path": "."},
            status=status,
        )
        session.add(task)
        await session.commit()
        return task.id


# --- create_task ---


@pytest.mark.asyncio
async def test_create_task_adds_pending_task(agent_session_factory, run_ctx):
    await _seed_run(agent_session_factory, run_ctx.run_id)

    out = await CreateTaskTool().run(
        CreateTaskInput(
            description="List root", tool_name="workspace.list_dir", tool_args={"path": "."}
        ),
        run_ctx,
    )
    assert out.sequence_index == 1

    async with agent_session_factory() as session:
        task = await session.get(AgentTask, out.task_id)
        assert task.status == TaskStatus.PENDING
        assert task.tool_name == "workspace.list_dir"


@pytest.mark.asyncio
async def test_create_task_rejects_unknown_tool(agent_session_factory, run_ctx):
    await _seed_run(agent_session_factory, run_ctx.run_id)

    with pytest.raises(ToolError):
        await CreateTaskTool().run(
            CreateTaskInput(description="d", tool_name="not_a_tool", tool_args={}), run_ctx
        )


@pytest.mark.asyncio
async def test_create_task_rejects_invalid_tool_args(agent_session_factory, run_ctx):
    await _seed_run(agent_session_factory, run_ctx.run_id)

    with pytest.raises(ToolError):
        await CreateTaskTool().run(
            CreateTaskInput(description="d", tool_name="workspace.write_file", tool_args={}),
            run_ctx,
        )


@pytest.mark.asyncio
async def test_create_task_wires_dependencies(agent_session_factory, run_ctx):
    await _seed_run(agent_session_factory, run_ctx.run_id)

    first = await CreateTaskTool().run(
        CreateTaskInput(
            description="first", tool_name="workspace.list_dir", tool_args={"path": "."}
        ),
        run_ctx,
    )
    second = await CreateTaskTool().run(
        CreateTaskInput(
            description="second",
            tool_name="workspace.list_dir",
            tool_args={"path": "."},
            depends_on=[first.task_id],
        ),
        run_ctx,
    )

    out = await GetTaskTool().run(GetTaskInput(task_id=second.task_id), run_ctx)
    assert out.depends_on == [first.task_id]


# --- list_tasks / get_task ---


@pytest.mark.asyncio
async def test_list_tasks_filters_by_status(agent_session_factory, run_ctx):
    await _seed_task(
        agent_session_factory, run_ctx.run_id, sequence_index=0, status=TaskStatus.COMPLETED
    )
    await _seed_task(
        agent_session_factory, run_ctx.run_id, sequence_index=1, status=TaskStatus.PENDING
    )

    out = await ListTasksTool().run(ListTasksInput(status=TaskStatus.PENDING), run_ctx)
    assert len(out.tasks) == 1
    assert out.tasks[0].status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_get_task_rejects_unknown_task(run_ctx):
    with pytest.raises(ToolError):
        await GetTaskTool().run(GetTaskInput(task_id="missing"), run_ctx)


@pytest.mark.asyncio
async def test_get_task_rejects_task_from_other_run(agent_session_factory, run_ctx):
    other_task_id = await _seed_task(agent_session_factory, run_id="other-run")
    with pytest.raises(ToolError):
        await GetTaskTool().run(GetTaskInput(task_id=other_task_id), run_ctx)


# --- update_status ---


@pytest.mark.asyncio
async def test_update_status_allows_pending_to_skipped(agent_session_factory, run_ctx):
    task_id = await _seed_task(agent_session_factory, run_ctx.run_id)
    out = await UpdateStatusTool().run(
        UpdateStatusInput(task_id=task_id, status=TaskStatus.SKIPPED, reason="not needed"),
        run_ctx,
    )
    assert out.status == TaskStatus.SKIPPED


@pytest.mark.asyncio
async def test_update_status_forbids_marking_completed(agent_session_factory, run_ctx):
    task_id = await _seed_task(agent_session_factory, run_ctx.run_id)
    with pytest.raises(ToolError):
        await UpdateStatusTool().run(
            UpdateStatusInput(task_id=task_id, status=TaskStatus.COMPLETED), run_ctx
        )


@pytest.mark.asyncio
async def test_update_status_forbids_transition_from_completed(agent_session_factory, run_ctx):
    task_id = await _seed_task(agent_session_factory, run_ctx.run_id, status=TaskStatus.COMPLETED)
    with pytest.raises(ToolError):
        await UpdateStatusTool().run(
            UpdateStatusInput(task_id=task_id, status=TaskStatus.CANCELLED), run_ctx
        )


# --- set_priority_deadline ---


@pytest.mark.asyncio
async def test_set_priority_deadline_updates_fields(agent_session_factory, run_ctx):
    task_id = await _seed_task(agent_session_factory, run_ctx.run_id)
    out = await SetPriorityDeadlineTool().run(
        SetPriorityDeadlineInput(task_id=task_id, priority=5, deadline="2026-12-31"), run_ctx
    )
    assert out.priority == 5
    assert out.deadline == "2026-12-31"


# --- add_dependency ---


@pytest.mark.asyncio
async def test_add_dependency_wires_edge(agent_session_factory, run_ctx):
    a = await _seed_task(agent_session_factory, run_ctx.run_id, sequence_index=0)
    b = await _seed_task(agent_session_factory, run_ctx.run_id, sequence_index=1)
    await AddDependencyTool().run(AddDependencyInput(task_id=b, depends_on_task_id=a), run_ctx)

    out = await GetTaskTool().run(GetTaskInput(task_id=b), run_ctx)
    assert out.depends_on == [a]


@pytest.mark.asyncio
async def test_add_dependency_rejects_self_dependency(agent_session_factory, run_ctx):
    a = await _seed_task(agent_session_factory, run_ctx.run_id)
    with pytest.raises(ToolError):
        await AddDependencyTool().run(AddDependencyInput(task_id=a, depends_on_task_id=a), run_ctx)


@pytest.mark.asyncio
async def test_add_dependency_rejects_cross_plan_version_dependency(
    agent_session_factory, run_ctx
):
    # task_selection only ever looks at the current plan_version -- a dependency on a
    # task from a different plan_version could never be satisfied and would silently
    # deadlock the dependent task rather than failing loudly, so this must be rejected.
    current = await _seed_task(agent_session_factory, run_ctx.run_id, plan_version=2)
    stale = await _seed_task(agent_session_factory, run_ctx.run_id, plan_version=1)
    with pytest.raises(ToolError):
        await AddDependencyTool().run(
            AddDependencyInput(task_id=current, depends_on_task_id=stale), run_ctx
        )


@pytest.mark.asyncio
async def test_add_dependency_rejects_cycle(agent_session_factory, run_ctx):
    a = await _seed_task(agent_session_factory, run_ctx.run_id, sequence_index=0)
    b = await _seed_task(agent_session_factory, run_ctx.run_id, sequence_index=1)
    await AddDependencyTool().run(AddDependencyInput(task_id=b, depends_on_task_id=a), run_ctx)

    with pytest.raises(ToolError):
        await AddDependencyTool().run(AddDependencyInput(task_id=a, depends_on_task_id=b), run_ctx)


# --- record_result ---


@pytest.mark.asyncio
async def test_record_result_sets_summary_without_changing_status(agent_session_factory, run_ctx):
    task_id = await _seed_task(agent_session_factory, run_ctx.run_id, status=TaskStatus.IN_PROGRESS)
    await RecordResultTool().run(
        RecordResultInput(task_id=task_id, note="halfway there"), run_ctx
    )

    async with agent_session_factory() as session:
        task = await session.get(AgentTask, task_id)
        assert task.result_summary == "halfway there"
        assert task.status == TaskStatus.IN_PROGRESS


# --- retry_task ---


@pytest.mark.asyncio
async def test_retry_task_resets_failed_task_and_bumps_retry_count(agent_session_factory, run_ctx):
    task_id = await _seed_task(agent_session_factory, run_ctx.run_id, status=TaskStatus.FAILED)
    async with agent_session_factory() as session:
        task = await session.get(AgentTask, task_id)
        task.error_message = "boom"
        task.retry_count = 2
        await session.commit()

    out = await RetryTaskTool().run(RetryTaskInput(task_id=task_id), run_ctx)
    assert out.status == TaskStatus.PENDING
    assert out.retry_count == 3

    async with agent_session_factory() as session:
        task = await session.get(AgentTask, task_id)
        assert task.error_message is None


@pytest.mark.asyncio
async def test_retry_task_rejects_non_failed_task(agent_session_factory, run_ctx):
    task_id = await _seed_task(agent_session_factory, run_ctx.run_id, status=TaskStatus.PENDING)
    with pytest.raises(ToolError):
        await RetryTaskTool().run(RetryTaskInput(task_id=task_id), run_ctx)


# --- cancel_task ---


@pytest.mark.asyncio
async def test_cancel_task_from_pending(agent_session_factory, run_ctx):
    task_id = await _seed_task(agent_session_factory, run_ctx.run_id)
    out = await CancelTaskTool().run(
        CancelTaskInput(task_id=task_id, reason="no longer needed"), run_ctx
    )
    assert out.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_task_rejects_from_completed(agent_session_factory, run_ctx):
    task_id = await _seed_task(agent_session_factory, run_ctx.run_id, status=TaskStatus.COMPLETED)
    with pytest.raises(ToolError):
        await CancelTaskTool().run(CancelTaskInput(task_id=task_id), run_ctx)
