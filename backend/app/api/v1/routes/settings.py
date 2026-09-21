from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.settings import SettingsResponse

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_current_settings(settings: Settings = Depends(get_settings)) -> SettingsResponse:
    return SettingsResponse(
        llm_provider=settings.llm_provider,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
        workspace_root=str(settings.resolved_workspace_root()),
        max_tasks_per_run=settings.max_tasks_per_run,
        max_retries_per_task=settings.max_retries_per_task,
        max_replanning_attempts=settings.max_replanning_attempts,
        max_run_duration_seconds=settings.max_run_duration_seconds,
        max_tool_calls_per_run=settings.max_tool_calls_per_run,
        approval_ttl_seconds=settings.approval_ttl_seconds,
        search_provider=settings.search_provider,
        browser_allowed_domains=settings.browser_allowed_domains,
        browser_headless=settings.browser_headless,
        python_runner_timeout_seconds=settings.python_runner_timeout_seconds,
        python_runner_memory_limit_mb=settings.python_runner_memory_limit_mb,
        python_runner_cpu_limit=settings.python_runner_cpu_limit,
    )
