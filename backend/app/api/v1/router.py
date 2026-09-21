from fastapi import APIRouter

from app.api.v1.routes import agent_runs, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(agent_runs.router)
