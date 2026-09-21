from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.enums import TaskStatus
from app.db.models.task_dependency import TaskDependency


class CreateTaskInput(BaseModel):
    description: str
    tool_name: str
    tool_args: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list, description="Existing task ids")
    priority: int = 0
    deadline: str | None = None


class CreateTaskOutput(BaseModel):
    task_id: str
    sequence_index: int


class CreateTaskTool(Tool):
    name = "task.create"
    category = ToolCategory.TASK_MANAGEMENT
    description = (
        "Add a new task to the current run's plan. It becomes eligible for execution "
        "as soon as its dependencies (if any) are completed."
    )
    input_schema = CreateTaskInput
    output_schema = CreateTaskOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: CreateTaskInput, ctx: ToolRunContext) -> CreateTaskOutput:
        target_tool = ctx.tool_registry.get(args.tool_name)
        if target_tool is None:
            raise ToolError(f"Unknown tool: {args.tool_name}")
        try:
            target_tool.input_schema.model_validate(args.tool_args)
        except ValidationError as exc:
            raise ToolError(f"Invalid tool_args for '{args.tool_name}': {exc}") from exc

        async with ctx.session_factory() as session:
            run = await session.get(AgentRun, ctx.run_id)
            if run is None:
                raise ToolError("Run not found")

            for dep_id in args.depends_on:
                dep = await session.get(AgentTask, dep_id)
                if dep is None or dep.run_id != ctx.run_id:
                    raise ToolError(f"Unknown dependency task: {dep_id}")

            next_seq = (
                await session.scalar(
                    select(func.max(AgentTask.sequence_index)).where(
                        AgentTask.run_id == ctx.run_id, AgentTask.plan_version == run.plan_version
                    )
                )
                or 0
            ) + 1

            new_task = AgentTask(
                run_id=ctx.run_id,
                plan_version=run.plan_version,
                sequence_index=next_seq,
                description=args.description,
                tool_name=args.tool_name,
                tool_args=args.tool_args,
                status=TaskStatus.PENDING,
                priority=args.priority,
                deadline=args.deadline,
            )
            session.add(new_task)
            await session.flush()

            for dep_id in args.depends_on:
                session.add(TaskDependency(task_id=new_task.id, depends_on_task_id=dep_id))

            await session.commit()
            return CreateTaskOutput(task_id=new_task.id, sequence_index=next_seq)
