from collections.abc import Awaitable, Callable

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState
from app.agent.nodes._context import NodeContext
from app.db.base import utcnow
from app.db.models.agent_run import AgentRun
from app.db.models.enums import EventSeverity, RunStatus

MAX_GOAL_LENGTH = 4000


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def goal_validation(state: AgentState) -> dict:
        goal = (state.get("goal") or "").strip()
        valid = 0 < len(goal) <= MAX_GOAL_LENGTH

        async with deps.session_factory() as session:
            ctx = NodeContext(session, state["run_id"], "goal_validation")
            run = await session.get(AgentRun, state["run_id"])
            assert run is not None

            if valid:
                run.status = RunStatus.RUNNING
                run.started_at = run.started_at or utcnow()
                await ctx.log_event("goal_validated", payload={"goal": goal})
            else:
                run.status = RunStatus.FAILED
                run.error_message = "Goal is empty or exceeds the maximum allowed length."
                await ctx.log_event(
                    "goal_invalid",
                    payload={"length": len(goal), "max_length": MAX_GOAL_LENGTH},
                    severity=EventSeverity.WARNING,
                )
            await session.commit()

        return {
            "goal_validated": valid,
            "clarification_needed": not valid,
            "status": RunStatus.RUNNING if valid else RunStatus.FAILED,
        }

    return goal_validation
