import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.approval_sweep import sweep_expired_approvals

settings = get_settings()
logger = logging.getLogger(__name__)

_SWEEP_INTERVAL_SECONDS = 60


async def _approval_sweep_loop() -> None:
    """Periodic hygiene sweep marking expired PENDING approvals as EXPIRED, so the UI
    reflects reality even if nobody happens to hit GET /approvals in the meantime.
    Not the actual enforcement point -- see services/approval_sweep.py."""
    while True:
        try:
            async with SessionLocal() as session:
                await sweep_expired_approvals(session)
        except Exception:
            logger.exception("Approval expiry sweep failed")
        await asyncio.sleep(_SWEEP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_approval_sweep_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

# Local-first tool: only the local Vite dev server origins are allowed by default.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root() -> dict:
    return {"name": settings.app_name, "status": "running"}
