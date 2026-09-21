from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.runner import run_graph
from app.agent.graph.state import build_initial_state
from app.agent.llm.factory import get_llm_provider
from app.agent.tools.registry import build_default_registry
from app.core.config import Settings, get_settings
from app.db.base import new_uuid, utcnow
from app.db.models.agent_run import AgentRun
from app.db.models.enums import RunStatus
from app.db.session import get_session
from app.schemas.agent_run import CreateRunRequest, RunResponse

router = APIRouter(prefix="/agent/runs", tags=["agent"])


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
        workspace_root=workspace_root,
    )
    session.add(run)
    await session.commit()

    deps = GraphDependencies(
        llm_provider=get_llm_provider(provider_name),
        tool_registry=build_default_registry(),
        settings=settings,
    )
    initial_state = build_initial_state(
        run_id=run.id,
        goal=body.goal,
        workspace_root=workspace_root,
        llm_provider=provider_name,
        model_name=run.model_name,
        max_retries_per_task=settings.max_retries_per_task,
        max_replanning_attempts=settings.max_replanning_attempts,
        max_plan_validation_attempts=settings.max_plan_validation_attempts,
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
