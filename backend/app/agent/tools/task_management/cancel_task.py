from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.db.models.agent_task import AgentTask
from app.db.models.enums import TaskStatus

_CANCELLABLE_FROM = {
    TaskStatus.PENDING,
    TaskStatus.READY,
    TaskStatus.BLOCKED_ON_APPROVAL,
    TaskStatus.FAILED,
}


class CancelTaskInput(BaseModel):
    task_id: str
    reason: str | None = None


class CancelTaskOutput(BaseModel):
    task_id: str
    status: TaskStatus


class CancelTaskTool(Tool):
    name = "task.cancel"
    category = ToolCategory.TASK_MANAGEMENT
    description = "Cancel a task that is no longer needed."
    input_schema = CancelTaskInput
    output_schema = CancelTaskOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: CancelTaskInput, ctx: ToolRunContext) -> CancelTaskOutput:
        async with ctx.session_factory() as session:
            task = await session.get(AgentTask, args.task_id)
            if task is None or task.run_id != ctx.run_id:
                raise ToolError(f"Unknown task: {args.task_id}")
            if task.status not in _CANCELLABLE_FROM:
                raise ToolError(f"Cannot cancel a task in status {task.status.value}")

            task.status = TaskStatus.CANCELLED
            if args.reason:
                task.error_message = args.reason
            await session.commit()

            return CancelTaskOutput(task_id=task.id, status=task.status)
