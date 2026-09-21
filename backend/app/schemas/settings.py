from pydantic import BaseModel


class SettingsResponse(BaseModel):
    """A read-only snapshot of the backend's current configuration.

    Settings are environment-driven (see app/core/config.py) and not editable through
    the API -- there is no persisted override store, so this endpoint only surfaces the
    values in effect, for display and for the Settings screen's connection-test panel.
    """

    llm_provider: str
    ollama_base_url: str
    ollama_model: str
    workspace_root: str
    max_tasks_per_run: int
    max_retries_per_task: int
    max_replanning_attempts: int
    max_run_duration_seconds: int
    max_tool_calls_per_run: int
    approval_ttl_seconds: int
    search_provider: str
    browser_allowed_domains: list[str]
    browser_headless: bool
    python_runner_timeout_seconds: int
    python_runner_memory_limit_mb: int
    python_runner_cpu_limit: float
