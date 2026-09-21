from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.agent_task import AgentTask
from app.db.models.enums import TaskStatus
from app.db.session import get_session
from app.schemas.agent_task import AgentTaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[AgentTaskResponse])
async def list_tasks(
    run_id: str | None = None,
    status: TaskStatus | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[AgentTaskResponse]:
    query = select(AgentTask).options(selectinload(AgentTask.dependencies))
    if run_id is not None:
        query = query.where(AgentTask.run_id == run_id)
    if status is not None:
        query = query.where(AgentTask.status == status)
    query = query.order_by(AgentTask.created_at.desc()).limit(500)

    tasks = await session.scalars(query)
    return [AgentTaskResponse.model_validate(task) for task in tasks]
