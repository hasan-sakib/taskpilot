from collections.abc import Awaitable, Callable

from pydantic import ValidationError

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState, PlanTask
from app.agent.nodes._context import NodeContext
from app.db.models.enums import EventSeverity


def _has_cycle(plan: list[PlanTask]) -> bool:
    by_id = {task.task_id: task for task in plan}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(by_id, WHITE)

    def visit(task_id: str) -> bool:
        color[task_id] = GRAY
        for dep_id in by_id[task_id].depends_on:
            if dep_id not in by_id:
                continue
            if color.get(dep_id) == GRAY:
                return True
            if color.get(dep_id) == WHITE and visit(dep_id):
                return True
        color[task_id] = BLACK
        return False

    return any(color[task_id] == WHITE and visit(task_id) for task_id in by_id)


def _validate_plan(plan: list[PlanTask], deps: GraphDependencies) -> list[str]:
    errors: list[str] = []
    if not plan:
        errors.append("Plan has no tasks")
        return errors

    task_ids = {task.task_id for task in plan}
    for task in plan:
        tool = deps.tool_registry.get(task.tool_name)
        if tool is None:
            errors.append(f"Unknown tool '{task.tool_name}' in task {task.task_id}")
            continue
        try:
            tool.input_schema.model_validate(task.tool_args)
        except ValidationError as exc:
            errors.append(f"Invalid args for '{task.tool_name}' in task {task.task_id}: {exc}")
        for dep_id in task.depends_on:
            if dep_id not in task_ids:
                errors.append(f"Task {task.task_id} depends on unknown task {dep_id}")

    if _has_cycle(plan):
        errors.append("Task dependency graph contains a cycle")

    return errors


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def plan_validation(state: AgentState) -> dict:
        plan = state.get("plan") or []
        errors = list(state.get("plan_validation_errors") or [])
        errors.extend(_validate_plan(plan, deps))
        attempts = state.get("plan_validation_attempts", 0) + 1

        async with deps.session_factory() as session:
            ctx = NodeContext(session, state["run_id"], "plan_validation")
            await ctx.log_event(
                "plan_validated" if not errors else "plan_invalid",
                payload={"errors": errors, "attempt": attempts},
                severity=EventSeverity.INFO if not errors else EventSeverity.WARNING,
            )
            await session.commit()

        return {"plan_validation_errors": errors, "plan_validation_attempts": attempts}

    return plan_validation
