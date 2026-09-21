from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.approval_request import ApprovalRequest
from app.db.models.enums import ApprovalStatus, RunStatus, TaskStatus
from app.services.approval_sweep import sweep_expired_approvals


async def _seed_approval(
    session: AsyncSession, *, status: ApprovalStatus, expires_at, suffix: str
) -> ApprovalRequest:
    run = AgentRun(
        id=f"run-{suffix}",
        goal="g",
        status=RunStatus.PAUSED_FOR_APPROVAL,
        workspace_root="/tmp",
    )
    task = AgentTask(
        id=f"task-{suffix}",
        run_id=run.id,
        sequence_index=0,
        description="d",
        tool_name="test.tool",
        status=TaskStatus.BLOCKED_ON_APPROVAL,
    )
    approval = ApprovalRequest(
        id=f"approval-{suffix}",
        run_id=run.id,
        task_id=task.id,
        action_type="test.tool",
        action_payload={},
        payload_hash="hash",
        status=status,
        requested_at=utcnow(),
        expires_at=expires_at,
    )
    session.add_all([run, task, approval])
    await session.commit()
    return approval


@pytest.mark.asyncio
async def test_sweep_marks_expired_pending_approvals_as_expired(db_session: AsyncSession):
    await _seed_approval(
        db_session,
        status=ApprovalStatus.PENDING,
        expires_at=utcnow() - timedelta(minutes=1),
        suffix="expired",
    )

    swept_count = await sweep_expired_approvals(db_session)

    assert swept_count == 1
    approval = await db_session.get(ApprovalRequest, "approval-expired")
    assert approval.status == ApprovalStatus.EXPIRED


@pytest.mark.asyncio
async def test_sweep_leaves_non_expired_pending_approvals_alone(db_session: AsyncSession):
    await _seed_approval(
        db_session,
        status=ApprovalStatus.PENDING,
        expires_at=utcnow() + timedelta(minutes=15),
        suffix="fresh",
    )

    swept_count = await sweep_expired_approvals(db_session)

    assert swept_count == 0
    approval = await db_session.get(ApprovalRequest, "approval-fresh")
    assert approval.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_sweep_does_not_touch_already_resolved_approvals(db_session: AsyncSession):
    await _seed_approval(
        db_session,
        status=ApprovalStatus.APPROVED,
        expires_at=utcnow() - timedelta(minutes=1),
        suffix="resolved",
    )

    swept_count = await sweep_expired_approvals(db_session)

    assert swept_count == 0
    approval = await db_session.get(ApprovalRequest, "approval-resolved")
    assert approval.status == ApprovalStatus.APPROVED


@pytest.mark.asyncio
async def test_sweep_returns_zero_when_nothing_pending(db_session: AsyncSession):
    assert await sweep_expired_approvals(db_session) == 0
