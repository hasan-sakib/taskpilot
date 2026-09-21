from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.db.models.agent_task import AgentTask
from app.db.models.enums import TaskStatus

# The agent may only ever *decide not to pursue* a task (skip/cancel it) through this
# tool -- COMPLETED must come from an actual successful tool_execution/result_verification
# pass, and IN_PROGRESS is system-managed. Letting a tool call fabricate "completed"
# would let the agent lie about work it never did.
_ALLOWED_MANUAL_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.SKIPPED, TaskStatus.CANCELLED},
    TaskStatus.BLOCKED_ON_APPROVAL: {TaskStatus.CANCELLED},
    TaskStatus.FAILED: {TaskStatus.CANCELLED},
}


class UpdateStatusInput(BaseModel):
    task_id: str
    status: TaskStatus
    reason: str | None = None


class UpdateStatusOutput(BaseModel):
    task_id: str
    status: TaskStatus


class UpdateStatusTool(Tool):
    name = "task.update_status"
    category = ToolCategory.TASK_MANAGEMENT
    description = (
        "Skip or cancel a task the agent has decided not to pursue. Cannot be used to "
        "mark a task completed -- that only happens through actually running it."
    )
    input_schema = UpdateStatusInput
    output_schema = UpdateStatusOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: UpdateStatusInput, ctx: ToolRunContext) -> UpdateStatusOutput:
        async with ctx.session_factory() as session:
            task = await session.get(AgentTask, args.task_id)
            if task is None or task.run_id != ctx.run_id:
                raise ToolError(f"Unknown task: {args.task_id}")

            allowed = _ALLOWED_MANUAL_TRANSITIONS.get(task.status, set())
            if args.status not in allowed:
                raise ToolError(
                    f"Cannot manually transition task from {task.status.value} to "
                    f"{args.status.value}. Allowed from {task.status.value}: "
                    f"{sorted(s.value for s in allowed) or 'none'}"
                )

            task.status = args.status
            if args.reason:
                task.error_message = args.reason
            await session.commit()

            return UpdateStatusOutput(task_id=task.id, status=task.status)
