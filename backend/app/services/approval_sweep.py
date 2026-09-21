from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models.approval_request import ApprovalRequest
from app.db.models.enums import ApprovalStatus


async def sweep_expired_approvals(session: AsyncSession) -> int:
    """Mark PENDING approvals past their expires_at as EXPIRED.

    This is UI/data hygiene, not the actual enforcement point: resolve_approval
    (app/agent/graph/approvals.py) independently re-checks expiry at resolution time
    regardless of whether a sweep has run recently, so a stale approval can never be
    replayed just because this hasn't fired yet.
    """
    now = utcnow()
    expired = list(
        await session.scalars(
            select(ApprovalRequest).where(
                ApprovalRequest.status == ApprovalStatus.PENDING,
                ApprovalRequest.expires_at < now,
            )
        )
    )
    for approval in expired:
        approval.status = ApprovalStatus.EXPIRED
    if expired:
        await session.commit()
    return len(expired)
