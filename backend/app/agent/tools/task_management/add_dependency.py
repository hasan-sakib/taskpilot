from pydantic import BaseModel
from sqlalchemy import select

from app.agent.policies.dependency_policy import has_cycle
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.db.models.agent_task import AgentTask
from app.db.models.task_dependency import TaskDependency


class AddDependencyInput(BaseModel):
    task_id: str
    depends_on_task_id: str


class AddDependencyOutput(BaseModel):
    task_id: str
    depends_on_task_id: str


class AddDependencyTool(Tool):
    name = "task.add_dependency"
    category = ToolCategory.TASK_MANAGEMENT
    description = "Declare that one task must complete before another may start."
    input_schema = AddDependencyInput
    output_schema = AddDependencyOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: AddDependencyInput, ctx: ToolRunContext) -> AddDependencyOutput:
        if args.task_id == args.depends_on_task_id:
            raise ToolError("A task cannot depend on itself")

        async with ctx.session_factory() as session:
            task = await session.get(AgentTask, args.task_id)
            if task is None or task.run_id != ctx.run_id:
                raise ToolError(f"Unknown task: {args.task_id}")
            dep_task = await session.get(AgentTask, args.depends_on_task_id)
            if dep_task is None or dep_task.run_id != ctx.run_id:
                raise ToolError(f"Unknown task: {args.depends_on_task_id}")
            if dep_task.plan_version != task.plan_version:
                # task_selection only ever looks at the current plan_version's tasks
                # and dependencies (see task_selection.py), so a dependency on a task
                # from a different plan_version could never be satisfied -- it would
                # silently pass the cycle check below (the referenced task isn't in
                # that plan_version's edge map) and then permanently deadlock the
                # dependent task instead of failing loudly here.
                raise ToolError(
                    f"Cannot depend on task {args.depends_on_task_id} "
                    f"(plan_version {dep_task.plan_version}): "
                    f"it is not part of the current plan_version ({task.plan_version})"
                )

            existing = list(
                await session.scalars(
                    select(TaskDependency).where(
                        TaskDependency.task_id.in_(
                            select(AgentTask.id).where(
                                AgentTask.run_id == ctx.run_id,
                                AgentTask.plan_version == task.plan_version,
                            )
                        )
                    )
                )
            )
            edges: dict[str, list[str]] = {}
            for dep in existing:
                edges.setdefault(dep.task_id, []).append(dep.depends_on_task_id)
            edges.setdefault(args.task_id, []).append(args.depends_on_task_id)

            if has_cycle(edges):
                raise ToolError(
                    f"Adding this dependency would create a cycle: "
                    f"{args.task_id} -> {args.depends_on_task_id}"
                )

            already_exists = any(
                d.task_id == args.task_id and d.depends_on_task_id == args.depends_on_task_id
                for d in existing
            )
            if not already_exists:
                session.add(
                    TaskDependency(
                        task_id=args.task_id, depends_on_task_id=args.depends_on_task_id
                    )
                )
                await session.commit()

            return AddDependencyOutput(
                task_id=args.task_id, depends_on_task_id=args.depends_on_task_id
            )
