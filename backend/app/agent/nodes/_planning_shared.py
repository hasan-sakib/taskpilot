from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState, PlanTask
from app.agent.llm.base import LLMProviderError, PlanRequest, PlanResponse, ToolSpec
from app.agent.nodes._context import NodeContext
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.enums import TaskStatus
from app.db.models.task_dependency import TaskDependency


async def generate_plan_response(
    deps: GraphDependencies,
    state: AgentState,
    *,
    prior_errors: list[str] | None = None,
    prior_results_summary: str | None = None,
) -> tuple[PlanResponse, str | None]:
    """Call the LLM provider for a plan, degrading to an empty (invalid) plan on failure
    rather than letting the exception crash the run."""
    tool_specs = [
        ToolSpec(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema.model_json_schema(),
        )
        for tool in deps.tool_registry.all()
    ]
    request = PlanRequest(
        goal=state["goal"],
        available_tools=tool_specs,
        preferences=state.get("user_preferences_snapshot", {}),
        prior_errors=prior_errors or [],
        prior_results_summary=prior_results_summary,
    )
    try:
        response = await deps.llm_provider.generate_plan(request)
        return response, None
    except LLMProviderError as exc:
        return PlanResponse(tasks=[]), str(exc)


async def persist_plan(
    session: AsyncSession,
    ctx: NodeContext,
    state: AgentState,
    plan_response: PlanResponse,
) -> tuple[list[PlanTask], int]:
    """Persist a freshly generated plan as a new plan_version and return the graph-state
    mirror of it. Tasks start PENDING; dependency indices are resolved to real task ids."""
    new_version = state.get("plan_version", 0) + 1
    run_id = state["run_id"]

    run = await session.get(AgentRun, run_id)
    assert run is not None
    run.plan_version = new_version

    db_tasks: list[AgentTask] = []
    for i, spec in enumerate(plan_response.tasks):
        db_task = AgentTask(
            run_id=run_id,
            plan_version=new_version,
            sequence_index=i,
            description=spec.description,
            tool_name=spec.tool_name,
            tool_args=spec.tool_args,
            status=TaskStatus.PENDING,
        )
        session.add(db_task)
        db_tasks.append(db_task)
    await session.flush()  # assign ids before wiring dependencies

    plan_tasks: list[PlanTask] = []
    for i, (spec, db_task) in enumerate(zip(plan_response.tasks, db_tasks, strict=True)):
        depends_on_ids = [db_tasks[j].id for j in spec.depends_on if 0 <= j < len(db_tasks)]
        for dep_id in depends_on_ids:
            session.add(TaskDependency(task_id=db_task.id, depends_on_task_id=dep_id))
        plan_tasks.append(
            PlanTask(
                task_id=db_task.id,
                sequence_index=i,
                description=spec.description,
                tool_name=spec.tool_name,
                tool_args=spec.tool_args,
                depends_on=depends_on_ids,
                status=TaskStatus.PENDING,
            )
        )

    await ctx.log_event(
        "plan_generated",
        payload={"plan_version": new_version, "task_count": len(plan_tasks)},
    )
    return plan_tasks, new_version
