from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.db.models.agent_task import AgentTask
from app.db.models.enums import TaskStatus


class RetryTaskInput(BaseModel):
    task_id: str


class RetryTaskOutput(BaseModel):
    task_id: str
    status: TaskStatus
    retry_count: int


class RetryTaskTool(Tool):
    name = "task.retry"
    category = ToolCategory.TASK_MANAGEMENT
    description = "Reset a failed task back to pending so it will be attempted again."
    input_schema = RetryTaskInput
    output_schema = RetryTaskOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: RetryTaskInput, ctx: ToolRunContext) -> RetryTaskOutput:
        async with ctx.session_factory() as session:
            task = await session.get(AgentTask, args.task_id)
            if task is None or task.run_id != ctx.run_id:
                raise ToolError(f"Unknown task: {args.task_id}")
            if task.status != TaskStatus.FAILED:
                raise ToolError(
                    f"Only a failed task can be retried (current status: {task.status.value})"
                )

            # Bumping retry_count here (not just resetting status) is what gives this
            # attempt sequence a distinct approval payload_hash if the task's tool
            # requires approval -- otherwise permission_evaluation would collide with
            # the already-resolved ApprovalRequest from the previous attempt and the
            # run would deadlock waiting on an approval nothing can ever resolve again.
            task.status = TaskStatus.PENDING
            task.retry_count += 1
            task.error_message = None
            await session.commit()

            return RetryTaskOutput(
                task_id=task.id, status=task.status, retry_count=task.retry_count
            )
