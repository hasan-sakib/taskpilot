from collections.abc import Awaitable, Callable

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState
from app.agent.nodes._context import NodeContext
from app.db.models.agent_task import AgentTask
from app.db.models.enums import EventSeverity, TaskStatus


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def retry_recovery(state: AgentState) -> dict:
        task_id = state["current_task_id"]
        assert task_id is not None
        max_retries = state.get("max_retries_per_task", deps.settings.max_retries_per_task)

        async with deps.session_factory() as session:
            ctx = NodeContext(session, state["run_id"], "retry_recovery")
            task = await session.get(AgentTask, task_id)
            assert task is not None

            if state.get("approval_decision") == "rejected":
                # A rejection is a deliberate "no", not a transient failure -- never retry
                # the same consequential action without a fresh approval request.
                task.status = TaskStatus.FAILED
                task.error_message = "Rejected by approval"
                await ctx.log_event(
                    "task_failed_rejected", task_id=task_id, severity=EventSeverity.WARNING
                )
                await session.commit()
                return {
                    "retry_recovery_outcome": "exhausted",
                    "retry_count": 0,
                    "approval_decision": None,
                }

            retry_count = state.get("retry_count", 0) + 1
            # Increment the DB column relative to its current value, never assign from
            # graph-state retry_count directly: graph-state resets to 0 on every replan
            # and on verification success, but task.retry_count must stay strictly
            # monotonic for the task's whole lifetime -- it's also what
            # compute_payload_hash uses (via permission_evaluation) to give a manually
            # retried attempt (task.retry tool) a fresh, resolvable ApprovalRequest.
            # Assigning here instead of incrementing let an automatic retry sequence
            # silently roll task.retry_count back down after a manual retry had already
            # pushed it higher, so a later manual retry could recompute the exact same
            # hash as a prior (already-resolved) attempt and deadlock the run waiting on
            # an approval nothing could ever resolve again.
            task.retry_count += 1
            if retry_count <= max_retries:
                await ctx.log_event(
                    "task_retry_scheduled",
                    task_id=task_id,
                    payload={"attempt": retry_count, "max_retries": max_retries},
                )
                await session.commit()
                return {"retry_recovery_outcome": "retry", "retry_count": retry_count}

            task.status = TaskStatus.FAILED
            await ctx.log_event(
                "task_retries_exhausted",
                task_id=task_id,
                payload={"attempts": retry_count},
                severity=EventSeverity.WARNING,
            )
            await session.commit()
            return {"retry_recovery_outcome": "exhausted", "retry_count": 0}

    return retry_recovery
