from collections.abc import Awaitable, Callable
from datetime import timedelta

from langgraph.types import interrupt
from sqlalchemy import select

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState, ToolCallRequest
from app.agent.nodes._context import NodeContext
from app.agent.policies.approval_policy import compute_payload_hash
from app.db.base import utcnow
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.approval_request import ApprovalRequest
from app.db.models.enums import ApprovalStatus, RunStatus, TaskStatus


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def permission_evaluation(state: AgentState) -> dict:
        run_id = state["run_id"]
        task_id = state["current_task_id"]
        assert task_id is not None

        async with deps.session_factory() as session:
            ctx = NodeContext(session, run_id, "permission_evaluation")
            task = await session.get(AgentTask, task_id)
            assert task is not None

            tool = deps.tool_registry.get(task.tool_name)
            assert tool is not None, f"Unknown tool at execution time: {task.tool_name}"

            payload_hash = compute_payload_hash(
                tool_name=tool.name,
                args=task.tool_args,
                target=None,
                run_id=run_id,
                task_id=task_id,
                workspace_root=state["workspace_root"],
                retry_count=task.retry_count,
            )
            decision = tool.evaluate_permission(
                task.tool_args, state.get("user_preferences_snapshot", {})
            )
            tool_call = ToolCallRequest(
                tool_name=tool.name,
                args=task.tool_args,
                target=None,
                payload_hash=payload_hash,
                requires_approval=decision.requires_approval,
            )

            if not decision.requires_approval:
                await ctx.log_event(
                    "permission_auto_approved", task_id=task_id, payload={"tool_name": tool.name}
                )
                await session.commit()
                return {
                    "current_tool_call": tool_call,
                    "approval_decision": "approved",
                    "pending_approval_id": None,
                }

            approval = await session.scalar(
                select(ApprovalRequest).where(
                    ApprovalRequest.run_id == run_id,
                    ApprovalRequest.task_id == task_id,
                    ApprovalRequest.payload_hash == payload_hash,
                )
            )
            if approval is None:
                now = utcnow()
                approval = ApprovalRequest(
                    run_id=run_id,
                    task_id=task_id,
                    action_type=tool.name,
                    target=None,
                    action_payload=task.tool_args,
                    payload_hash=payload_hash,
                    status=ApprovalStatus.PENDING,
                    requested_at=now,
                    expires_at=now + timedelta(seconds=deps.settings.approval_ttl_seconds),
                )
                session.add(approval)
                await session.flush()
                task.status = TaskStatus.BLOCKED_ON_APPROVAL
                run = await session.get(AgentRun, run_id)
                assert run is not None
                run.status = RunStatus.PAUSED_FOR_APPROVAL
                await ctx.log_event(
                    "approval_requested", task_id=task_id, payload={"approval_id": approval.id}
                )
            approval_id = approval.id
            await session.commit()

            # Everything above must be safe to re-run: on resume, LangGraph replays this
            # node from the top and interrupt() simply returns the resume value instead
            # of pausing again. The idempotent select-or-create above makes that safe.
            resume_value = interrupt(
                {
                    "approval_id": approval_id,
                    "tool_name": tool.name,
                    "args": task.tool_args,
                }
            )

        decision_str = resume_value.get("decision") if isinstance(resume_value, dict) else None
        return {
            "current_tool_call": tool_call,
            "approval_decision": decision_str,
            "pending_approval_id": approval_id,
        }

    return permission_evaluation
