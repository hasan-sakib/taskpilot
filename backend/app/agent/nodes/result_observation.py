from collections.abc import Awaitable, Callable

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState
from app.agent.nodes._context import NodeContext
from app.db.models.enums import EventSeverity


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def result_observation(state: AgentState) -> dict:
        result = state["last_tool_result"]
        task_id = state["current_task_id"]

        async with deps.session_factory() as session:
            ctx = NodeContext(session, state["run_id"], "result_observation")
            await ctx.log_event(
                "tool_result_observed",
                task_id=task_id,
                payload={
                    "success": result.success,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                },
                severity=EventSeverity.INFO if result.success else EventSeverity.WARNING,
            )
            await session.commit()

        return {}

    return result_observation
