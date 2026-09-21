from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.browser.session_manager import get_session_manager
from app.db.models.browser_session import BrowserSession
from app.db.session import get_session
from app.schemas.browser_session import BrowserSessionResponse

router = APIRouter(prefix="/browser", tags=["browser"])


@router.get("/sessions", response_model=list[BrowserSessionResponse])
async def list_browser_sessions(
    run_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[BrowserSessionResponse]:
    query = select(BrowserSession)
    if run_id is not None:
        query = query.where(BrowserSession.run_id == run_id)
    query = query.order_by(BrowserSession.created_at.desc()).limit(100)

    sessions = await session.scalars(query)
    manager = get_session_manager()
    return [
        BrowserSessionResponse(
            id=s.id,
            run_id=s.run_id,
            task_id=s.task_id,
            status=s.status,
            current_url=s.current_url,
            headless=s.headless,
            started_at=s.started_at,
            closed_at=s.closed_at,
            is_live=manager.is_active(s.id),
        )
        for s in sessions
    ]
