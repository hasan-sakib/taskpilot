from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.db.models.agent_task import AgentTask


class SetPriorityDeadlineInput(BaseModel):
    task_id: str
    priority: int | None = None
    deadline: str | None = None


class SetPriorityDeadlineOutput(BaseModel):
    task_id: str
    priority: int
    deadline: str | None


class SetPriorityDeadlineTool(Tool):
    name = "task.set_priority_deadline"
    category = ToolCategory.TASK_MANAGEMENT
    description = "Set a task's priority and/or deadline metadata."
    input_schema = SetPriorityDeadlineInput
    output_schema = SetPriorityDeadlineOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(
        self, args: SetPriorityDeadlineInput, ctx: ToolRunContext
    ) -> SetPriorityDeadlineOutput:
        async with ctx.session_factory() as session:
            task = await session.get(AgentTask, args.task_id)
            if task is None or task.run_id != ctx.run_id:
                raise ToolError(f"Unknown task: {args.task_id}")

            if args.priority is not None:
                task.priority = args.priority
            if args.deadline is not None:
                task.deadline = args.deadline
            await session.commit()

            return SetPriorityDeadlineOutput(
                task_id=task.id, priority=task.priority, deadline=task.deadline
            )
