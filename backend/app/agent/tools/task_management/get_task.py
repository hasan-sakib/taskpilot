from pydantic import BaseModel
from sqlalchemy import select

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.db.models.agent_task import AgentTask
from app.db.models.enums import TaskStatus
from app.db.models.task_dependency import TaskDependency


class GetTaskInput(BaseModel):
    task_id: str


class GetTaskOutput(BaseModel):
    task_id: str
    sequence_index: int
    description: str
    tool_name: str
    tool_args: dict
    status: TaskStatus
    priority: int
    deadline: str | None
    retry_count: int
    result_summary: str | None
    error_message: str | None
    depends_on: list[str]


class GetTaskTool(Tool):
    name = "task.get"
    category = ToolCategory.TASK_MANAGEMENT
    description = "Get full details for a single task, including its dependencies."
    input_schema = GetTaskInput
    output_schema = GetTaskOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: GetTaskInput, ctx: ToolRunContext) -> GetTaskOutput:
        async with ctx.session_factory() as session:
            task = await session.get(AgentTask, args.task_id)
            if task is None or task.run_id != ctx.run_id:
                raise ToolError(f"Unknown task: {args.task_id}")

            depends_on = list(
                await session.scalars(
                    select(TaskDependency.depends_on_task_id).where(
                        TaskDependency.task_id == args.task_id
                    )
                )
            )

            return GetTaskOutput(
                task_id=task.id,
                sequence_index=task.sequence_index,
                description=task.description,
                tool_name=task.tool_name,
                tool_args=task.tool_args,
                status=task.status,
                priority=task.priority,
                deadline=task.deadline,
                retry_count=task.retry_count,
                result_summary=task.result_summary,
                error_message=task.error_message,
                depends_on=depends_on,
            )
