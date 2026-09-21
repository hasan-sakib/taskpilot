from fastapi import APIRouter

from app.api.v1.routes import (
    agent_runs,
    approvals,
    browser,
    health,
    preferences,
    settings,
    tasks,
    workspace,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(agent_runs.router)
api_router.include_router(approvals.router)
api_router.include_router(preferences.router)
api_router.include_router(tasks.router)
api_router.include_router(workspace.router)
api_router.include_router(browser.router)
api_router.include_router(settings.router)
