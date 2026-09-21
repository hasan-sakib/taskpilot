from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph.approvals import ApprovalResolutionError, resolve_approval
from app.core.config import Settings, get_settings
from app.db.models.agent_run import AgentRun
from app.db.models.approval_request import ApprovalRequest
from app.db.models.enums import ApprovalStatus
from app.db.session import get_session
from app.schemas.approval import ApprovalResponse, ResolveApprovalRequest
from app.services.approval_sweep import sweep_expired_approvals
from app.services.graph_dependencies import build_graph_dependencies, provider_name_for_run

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalResponse])
async def list_approvals(
    status: ApprovalStatus | None = None,
    run_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[ApprovalRequest]:
    await sweep_expired_approvals(session)

    query = select(ApprovalRequest).order_by(ApprovalRequest.requested_at.desc())
    if status is not None:
        query = query.where(ApprovalRequest.status == status)
    if run_id is not None:
        query = query.where(ApprovalRequest.run_id == run_id)
    return list(await session.scalars(query))


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str, session: AsyncSession = Depends(get_session)
) -> ApprovalRequest:
    approval = await session.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail=f"No such approval: {approval_id}")
    return approval


async def _resolve(
    approval_id: str,
    decision: str,
    body: ResolveApprovalRequest,
    session: AsyncSession,
    settings: Settings,
) -> ApprovalRequest:
    approval = await session.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail=f"No such approval: {approval_id}")

    run = await session.get(AgentRun, approval.run_id)
    assert run is not None
    deps = build_graph_dependencies(settings, provider_name_for_run(run))

    try:
        await resolve_approval(
            approval_id,
            decision,
            deps,
            resolved_by=body.resolved_by,
            rejection_reason=body.rejection_reason,
        )
    except ApprovalResolutionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await session.refresh(approval)
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_approval(
    approval_id: str,
    body: ResolveApprovalRequest = ResolveApprovalRequest(),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApprovalRequest:
    return await _resolve(approval_id, "approved", body, session, settings)


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
async def reject_approval(
    approval_id: str,
    body: ResolveApprovalRequest = ResolveApprovalRequest(),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ApprovalRequest:
    return await _resolve(approval_id, "rejected", body, session, settings)
