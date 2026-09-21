from collections.abc import Awaitable, Callable

from sqlalchemy import select

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState
from app.agent.nodes._context import NodeContext
from app.db.models.agent_task import AgentTask
from app.db.models.enums import RunStatus, TaskStatus


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def completion_evaluation(state: AgentState) -> dict:
        run_id = state["run_id"]
        plan_version = state.get("plan_version", 0)
        replanning_count = state.get("replanning_count", 0)
        max_replanning = state.get(
            "max_replanning_attempts", deps.settings.max_replanning_attempts
        )

        async with deps.session_factory() as session:
            ctx = NodeContext(session, run_id, "completion_evaluation")
            tasks = list(
                await session.scalars(
                    select(AgentTask).where(
                        AgentTask.run_id == run_id, AgentTask.plan_version == plan_version
                    )
                )
            )
            failed = [t for t in tasks if t.status == TaskStatus.FAILED]

            if failed and replanning_count < max_replanning:
                await ctx.log_event(
                    "completion_more_work",
                    payload={"failed_task_ids": [t.id for t in failed]},
                )
                await session.commit()
                return {"completion_outcome": "more_work"}

            final_status = RunStatus.FAILED if failed else RunStatus.COMPLETED
            await ctx.log_event(
                "completion_done",
                payload={"final_status": final_status.value, "failed_count": len(failed)},
            )
            await session.commit()
            return {"completion_outcome": "done", "status": final_status}

    return completion_evaluation
