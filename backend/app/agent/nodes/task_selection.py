from collections.abc import Awaitable, Callable

from sqlalchemy import func, select

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState
from app.agent.nodes._context import NodeContext
from app.db.base import utcnow
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.enums import EventSeverity, RunStatus, TaskStatus, ToolExecutionStatus
from app.db.models.task_dependency import TaskDependency
from app.db.models.tool_execution import ToolExecution

TERMINAL_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.SKIPPED,
    TaskStatus.CANCELLED,
}


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def task_selection(state: AgentState) -> dict:
        settings = deps.settings
        run_id = state["run_id"]

        async with deps.session_factory() as session:
            ctx = NodeContext(session, run_id, "task_selection")
            run = await session.get(AgentRun, run_id)
            assert run is not None

            if run.cancel_requested:
                await ctx.log_event("run_cancelled", severity=EventSeverity.WARNING)
                run.status = RunStatus.CANCELLED
                run.error_message = "Run was cancelled"
                await session.commit()
                return {
                    "task_selection_outcome": "cancelled",
                    "current_task_id": None,
                    "status": RunStatus.CANCELLED,
                }

            if run.started_at and (
                (utcnow() - run.started_at).total_seconds() > settings.max_run_duration_seconds
            ):
                await ctx.log_event("run_duration_limit_exceeded", severity=EventSeverity.WARNING)
                run.status = RunStatus.FAILED
                run.error_message = (
                    f"Execution limit exceeded: run exceeded "
                    f"max_run_duration_seconds ({settings.max_run_duration_seconds}s)"
                )
                await session.commit()
                return {
                    "task_selection_outcome": "limit_exceeded",
                    "current_task_id": None,
                    "status": RunStatus.FAILED,
                }

            total_executed = await session.scalar(
                select(func.count())
                .select_from(AgentTask)
                .where(AgentTask.run_id == run_id, AgentTask.status.in_(TERMINAL_STATUSES))
            )
            if (total_executed or 0) >= settings.max_tasks_per_run:
                await ctx.log_event("task_count_limit_exceeded", severity=EventSeverity.WARNING)
                run.status = RunStatus.FAILED
                run.error_message = (
                    f"Execution limit exceeded: run reached "
                    f"max_tasks_per_run ({settings.max_tasks_per_run})"
                )
                await session.commit()
                return {
                    "task_selection_outcome": "limit_exceeded",
                    "current_task_id": None,
                    "status": RunStatus.FAILED,
                }

            tool_call_count = await session.scalar(
                select(func.count())
                .select_from(ToolExecution)
                .where(
                    ToolExecution.run_id == run_id,
                    ToolExecution.status != ToolExecutionStatus.CANCELLED,
                )
            )
            if (tool_call_count or 0) >= settings.max_tool_calls_per_run:
                await ctx.log_event("tool_call_limit_exceeded", severity=EventSeverity.WARNING)
                run.status = RunStatus.FAILED
                run.error_message = (
                    f"Execution limit exceeded: run reached "
                    f"max_tool_calls_per_run ({settings.max_tool_calls_per_run})"
                )
                await session.commit()
                return {
                    "task_selection_outcome": "limit_exceeded",
                    "current_task_id": None,
                    "status": RunStatus.FAILED,
                }

            plan_version = state.get("plan_version", 0)
            all_tasks = list(
                await session.scalars(
                    select(AgentTask)
                    .where(AgentTask.run_id == run_id, AgentTask.plan_version == plan_version)
                    .order_by(AgentTask.sequence_index)
                )
            )
            status_by_id = {task.id: task.status for task in all_tasks}

            dep_rows = list(
                await session.scalars(
                    select(TaskDependency).where(
                        TaskDependency.task_id.in_([t.id for t in all_tasks])
                    )
                )
            )
            deps_by_task: dict[str, list[str]] = {}
            for dep in dep_rows:
                deps_by_task.setdefault(dep.task_id, []).append(dep.depends_on_task_id)

            pending = [t for t in all_tasks if t.status == TaskStatus.PENDING]
            runnable = next(
                (
                    t
                    for t in pending
                    if all(
                        status_by_id.get(dep_id) == TaskStatus.COMPLETED
                        for dep_id in deps_by_task.get(t.id, [])
                    )
                ),
                None,
            )

            if runnable is not None:
                await ctx.log_event("task_selected", task_id=runnable.id)
                await session.commit()
                return {"task_selection_outcome": "runnable", "current_task_id": runnable.id}

            if pending:
                await ctx.log_event(
                    "tasks_blocked",
                    payload={"pending_task_ids": [t.id for t in pending]},
                    severity=EventSeverity.WARNING,
                )
                await session.commit()
                return {"task_selection_outcome": "blocked", "current_task_id": None}

            await ctx.log_event("all_tasks_done")
            await session.commit()
            return {"task_selection_outcome": "all_done", "current_task_id": None}

    return task_selection
