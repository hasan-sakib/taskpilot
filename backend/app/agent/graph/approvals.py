from typing import Literal

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.runner import resume_graph
from app.db.base import utcnow
from app.db.models.agent_run import AgentRun
from app.db.models.approval_request import ApprovalRequest
from app.db.models.enums import ApprovalStatus, RunStatus


class ApprovalResolutionError(Exception):
    """Raised when an approval can't be resolved as requested."""


async def resolve_approval(
    approval_id: str,
    decision: Literal["approved", "rejected"],
    deps: GraphDependencies,
    *,
    resolved_by: str | None = None,
    rejection_reason: str | None = None,
) -> dict:
    """Transition an ApprovalRequest and resume the graph run it's blocking.

    This is the one place ApprovalRequest.status moves off `pending` -- without it the
    approval row would sit `pending` forever even after the graph has already acted on
    the decision, which is exactly the kind of drift the DB-vs-checkpoint design is
    meant to prevent. The Phase 4 approve/reject API routes call this directly; this
    function is deliberately not HTTP-specific so tests can call it the same way.
    """
    async with deps.session_factory() as session:
        approval = await session.get(ApprovalRequest, approval_id)
        if approval is None:
            raise ApprovalResolutionError(f"No such approval request: {approval_id}")
        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalResolutionError(
                f"Approval {approval_id} is not pending (status={approval.status.value})"
            )

        now = utcnow()
        if approval.expires_at < now:
            approval.status = ApprovalStatus.EXPIRED
            await session.commit()
            raise ApprovalResolutionError(f"Approval {approval_id} has expired")

        approval.status = (
            ApprovalStatus.APPROVED if decision == "approved" else ApprovalStatus.REJECTED
        )
        approval.resolved_at = now
        approval.resolved_by = resolved_by
        approval.rejection_reason = rejection_reason
        run_id = approval.run_id

        run = await session.get(AgentRun, run_id)
        assert run is not None
        run.status = RunStatus.RUNNING
        await session.commit()

    return await resume_graph(run_id, {"decision": decision}, deps)
