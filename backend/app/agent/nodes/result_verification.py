import json
from collections.abc import Awaitable, Callable

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState
from app.agent.nodes._context import NodeContext
from app.db.models.agent_task import AgentTask
from app.db.models.enums import EventSeverity, TaskStatus

RESULT_SUMMARY_MAX_CHARS = 2000


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def result_verification(state: AgentState) -> dict:
        result = state["last_tool_result"]
        task_id = state["current_task_id"]
        assert task_id is not None

        async with deps.session_factory() as session:
            ctx = NodeContext(session, state["run_id"], "result_verification")
            task = await session.get(AgentTask, task_id)
            assert task is not None

            if result.success:
                task.status = TaskStatus.COMPLETED
                task.result_summary = json.dumps(result.data or {})[:RESULT_SUMMARY_MAX_CHARS]
                await ctx.log_event("task_completed", task_id=task_id)
                await session.commit()
                return {"retry_count": 0}

            task.error_message = result.error
            await ctx.log_event(
                "task_attempt_failed",
                task_id=task_id,
                payload={"error": result.error},
                severity=EventSeverity.WARNING,
            )
            await session.commit()
            return {}

    return result_verification

