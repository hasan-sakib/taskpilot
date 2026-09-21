from fastapi import APIRouter

from app.api.v1.routes import agent_runs, approvals, health, preferences

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(agent_runs.router)
api_router.include_router(approvals.router)
api_router.include_router(preferences.router)
