from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph.runner import run_graph
from app.agent.graph.state import build_initial_state
from app.core.config import Settings, get_settings
from app.db.base import new_uuid, utcnow
from app.db.models.agent_event import AgentEvent
from app.db.models.agent_run import AgentRun
from app.db.models.enums import RunStatus
from app.db.session import get_session
from app.memory.preferences import load_confirmed_preferences_snapshot
from app.schemas.agent_event import AgentEventResponse
from app.schemas.agent_run import CreateRunRequest, RunResponse
from app.services.graph_dependencies import build_graph_dependencies

router = APIRouter(prefix="/agent/runs", tags=["agent"])


@router.get("", response_model=list[RunResponse])
async def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[RunResponse]:
    runs = await session.scalars(
        select(AgentRun).order_by(AgentRun.created_at.desc()).limit(limit)
    )
    return [RunResponse.model_validate(run) for run in runs]


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    body: CreateRunRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RunResponse:
    provider_name = body.llm_provider or settings.llm_provider
    workspace_root = str(settings.resolved_workspace_root())

    run = AgentRun(
        id=new_uuid(),
        goal=body.goal,
        status=RunStatus.PENDING,
        model_name=settings.ollama_model if provider_name == "ollama" else None,
        test_mode=provider_name == "test",
        workspace_root=workspace_root,
    )
    session.add(run)
    await session.commit()

    deps = build_graph_dependencies(settings, provider_name)
    preferences_snapshot = await load_confirmed_preferences_snapshot(session)
    initial_state = build_initial_state(
        run_id=run.id,
        goal=body.goal,
        workspace_root=workspace_root,
        llm_provider=provider_name,
        model_name=run.model_name,
        max_retries_per_task=settings.max_retries_per_task,
        max_replanning_attempts=settings.max_replanning_attempts,
        max_plan_validation_attempts=settings.max_plan_validation_attempts,
        user_preferences_snapshot=preferences_snapshot,
    )

    try:
        await run_graph(run.id, initial_state, deps)
    except Exception as exc:  # a node bug must not corrupt run state silently
        run.status = RunStatus.FAILED
        run.error_message = f"Unexpected error during execution: {exc}"
        run.completed_at = utcnow()
        await session.commit()
        raise HTTPException(status_code=500, detail=run.error_message) from exc

    await session.refresh(run)
    return RunResponse.model_validate(run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)) -> RunResponse:
    run = await session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No such run: {run_id}")
    return RunResponse.model_validate(run)


@router.get("/{run_id}/events", response_model=list[AgentEventResponse])
async def list_run_events(
    run_id: str, session: AsyncSession = Depends(get_session)
) -> list[AgentEventResponse]:
    run = await session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No such run: {run_id}")

    events = await session.scalars(
        select(AgentEvent)
        .where(AgentEvent.run_id == run_id)
        .order_by(AgentEvent.created_at.asc())
    )
    return [AgentEventResponse.model_validate(event) for event in events]


@router.post("/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(run_id: str, session: AsyncSession = Depends(get_session)) -> RunResponse:
    run = await session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No such run: {run_id}")
    if run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
        raise HTTPException(
            status_code=409, detail=f"Run is already terminal (status={run.status.value})"
        )

    # Cooperative cancellation: task_selection checks this flag at the top of every
    # cycle (the graph has no true mid-node preemption) and routes to a CANCELLED
    # terminal state on its next pass -- this just sets the flag; it doesn't (and
    # can't, from this concurrent request) stop an in-flight tool call immediately.
    run.cancel_requested = True
    await session.commit()
    return RunResponse.model_validate(run)
