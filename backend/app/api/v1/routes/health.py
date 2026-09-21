import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session

router = APIRouter(prefix="/health", tags=["health"])


class OllamaStatus(BaseModel):
    reachable: bool
    base_url: str
    model: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    database: bool
    ollama: OllamaStatus


@router.get("", response_model=HealthResponse)
async def health(session: AsyncSession = Depends(get_session)) -> HealthResponse:
    settings = get_settings()

    db_ok = True
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    ollama_reachable = False
    ollama_detail: str | None = None
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_reachable = resp.status_code == 200
    except Exception as exc:  # local dev tool: Ollama may simply not be running
        ollama_detail = str(exc)

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database=db_ok,
        ollama=OllamaStatus(
            reachable=ollama_reachable,
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            detail=ollama_detail,
        ),
    )
