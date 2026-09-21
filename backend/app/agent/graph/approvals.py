from typing import Literal

from sqlalchemy import update

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
        now = utcnow()
        new_status = (
            ApprovalStatus.APPROVED if decision == "approved" else ApprovalStatus.REJECTED
        )

        # A conditional UPDATE (compare-and-swap on status), not a read-then-write --
        # two concurrent resolve calls for the same approval must not both pass a
        # Python-side `if status == PENDING` check before either has committed. Only
        # the call whose UPDATE actually flips a still-PENDING, still-unexpired row can
        # proceed to resume the run; the loser sees rowcount == 0 and gets a 409-worthy
        # error instead of racing it into a double resume.
        cas_result = await session.execute(
            update(ApprovalRequest)
            .where(
                ApprovalRequest.id == approval_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
                ApprovalRequest.expires_at >= now,
            )
            .values(
                status=new_status,
                resolved_at=now,
                resolved_by=resolved_by,
                rejection_reason=rejection_reason,
            )
        )

        if cas_result.rowcount == 0:
            # Opportunistically flip a genuinely-expired-but-still-pending row to
            # EXPIRED via the same CAS pattern (mirrors the periodic sweep), so a
            # concurrent resolver can't race past this check either.
            await session.execute(
                update(ApprovalRequest)
                .where(
                    ApprovalRequest.id == approval_id,
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                    ApprovalRequest.expires_at < now,
                )
                .values(status=ApprovalStatus.EXPIRED)
            )
            await session.commit()

            approval = await session.get(ApprovalRequest, approval_id)
            if approval is None:
                raise ApprovalResolutionError(f"No such approval request: {approval_id}")
            raise ApprovalResolutionError(
                f"Approval {approval_id} is not pending (status={approval.status.value})"
            )

        approval = await session.get(ApprovalRequest, approval_id)
        assert approval is not None
        run_id = approval.run_id

        run = await session.get(AgentRun, run_id)
        assert run is not None
        run.status = RunStatus.RUNNING
        await session.commit()

    return await resume_graph(run_id, {"decision": decision}, deps)
