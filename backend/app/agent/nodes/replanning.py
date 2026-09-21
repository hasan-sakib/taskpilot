from collections.abc import Awaitable, Callable

from sqlalchemy import select

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState
from app.agent.nodes._context import NodeContext
from app.agent.nodes._planning_shared import generate_plan_response, persist_plan
from app.db.models.agent_task import AgentTask
from app.db.models.enums import EventSeverity, RunStatus


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def replanning(state: AgentState) -> dict:
        replanning_count = state.get("replanning_count", 0)
        max_replanning = state.get(
            "max_replanning_attempts", deps.settings.max_replanning_attempts
        )

        if replanning_count >= max_replanning:
            async with deps.session_factory() as session:
                ctx = NodeContext(session, state["run_id"], "replanning")
                await ctx.log_event(
                    "replanning_attempts_exhausted",
                    payload={"attempts": replanning_count},
                    severity=EventSeverity.WARNING,
                )
                await session.commit()
            return {"status": RunStatus.FAILED, "replanning_count": replanning_count}

        prior_version = state.get("plan_version", 0)
        async with deps.session_factory() as session:
            tasks = list(
                await session.scalars(
                    select(AgentTask).where(
                        AgentTask.run_id == state["run_id"],
                        AgentTask.plan_version == prior_version,
                    )
                )
            )
        prior_errors = state.get("plan_validation_errors") or []
        prior_summary = "\n".join(
            f"- {t.description}: {t.status.value}"
            + (f" ({t.error_message})" if t.error_message else "")
            for t in tasks
        )

        plan_response, provider_error = await generate_plan_response(
            deps, state, prior_errors=prior_errors, prior_results_summary=prior_summary or None
        )

        async with deps.session_factory() as session:
            ctx = NodeContext(session, state["run_id"], "replanning")
            plan_tasks, new_version = await persist_plan(session, ctx, state, plan_response)
            if provider_error:
                await ctx.log_event("replanning_provider_error", payload={"error": provider_error})
            await session.commit()

        return {
            "plan": plan_tasks,
            "plan_version": new_version,
            "plan_validation_errors": [provider_error] if provider_error else [],
            "plan_validation_attempts": 0,
            "replanning_count": replanning_count + 1,
            "retry_count": 0,
        }

    return replanning
