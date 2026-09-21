from collections.abc import Awaitable, Callable

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState
from app.agent.nodes._context import NodeContext
from app.agent.nodes._planning_shared import generate_plan_response, persist_plan


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def planning(state: AgentState) -> dict:
        # On a plan_validation-rejected retry (route_plan_validation loops back here,
        # not to replanning, while attempts remain), state already holds the errors
        # from the previous attempt -- passing them through is what lets a model
        # actually correct a schema-invalid plan instead of regenerating the same
        # rejected plan every attempt (this call runs at temperature=0). On the very
        # first attempt this is just the empty list build_initial_state seeds.
        prior_errors = state.get("plan_validation_errors") or []
        plan_response, error = await generate_plan_response(
            deps, state, prior_errors=prior_errors
        )

        async with deps.session_factory() as session:
            ctx = NodeContext(session, state["run_id"], "planning")
            plan_tasks, new_version = await persist_plan(session, ctx, state, plan_response)
            if error:
                await ctx.log_event("planning_provider_error", payload={"error": error})
            await session.commit()

        errors = [error] if error else []
        return {
            "plan": plan_tasks,
            "plan_version": new_version,
            "plan_validation_errors": errors,
        }

    return planning
