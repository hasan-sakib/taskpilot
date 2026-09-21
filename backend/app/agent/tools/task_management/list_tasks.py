from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolRunContext
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.enums import TaskStatus


class ListTasksInput(BaseModel):
    status: TaskStatus | None = None
    current_plan_only: bool = Field(
        default=True, description="If true, only list tasks from the current plan version"
    )


class TaskSummary(BaseModel):
    task_id: str
    sequence_index: int
    description: str
    tool_name: str
    status: TaskStatus
    priority: int
    deadline: str | None


class ListTasksOutput(BaseModel):
    tasks: list[TaskSummary]


class ListTasksTool(Tool):
    name = "task.list"
    category = ToolCategory.TASK_MANAGEMENT
    description = "List tasks for the current run, optionally filtered by status."
    input_schema = ListTasksInput
    output_schema = ListTasksOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: ListTasksInput, ctx: ToolRunContext) -> ListTasksOutput:
        async with ctx.session_factory() as session:
            query = select(AgentTask).where(AgentTask.run_id == ctx.run_id)
            if args.current_plan_only:
                run = await session.get(AgentRun, ctx.run_id)
                if run is not None:
                    query = query.where(AgentTask.plan_version == run.plan_version)
            if args.status is not None:
                query = query.where(AgentTask.status == args.status)
            query = query.order_by(AgentTask.sequence_index)

            tasks = list(await session.scalars(query))
            return ListTasksOutput(
                tasks=[
                    TaskSummary(
                        task_id=t.id,
                        sequence_index=t.sequence_index,
                        description=t.description,
                        tool_name=t.tool_name,
                        status=t.status,
                        priority=t.priority,
                        deadline=t.deadline,
                    )
                    for t in tasks
                ]
            )
