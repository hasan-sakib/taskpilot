from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TASKPILOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "TaskPilot"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    # --- Server binding (localhost by default; never expose publicly without review) ---
    host: str = "127.0.0.1"
    port: int = 8000

    # --- Data locations ---
    data_dir: Path = Path("data")
    workspace_root: Path = Path("../workspace")

    @property
    def app_db_path(self) -> Path:
        return self.data_dir / "taskpilot.db"

    @property
    def checkpoint_db_path(self) -> Path:
        return self.data_dir / "checkpoints.db"

    @property
    def app_db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.app_db_path}"

    @property
    def sync_app_db_url(self) -> str:
        """Used by Alembic, which runs migrations synchronously."""
        return f"sqlite:///{self.app_db_path}"

    # --- LLM provider ---
    llm_provider: str = "ollama"  # "ollama" | "test"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    # 120s was the original default; a real integration run against qwen3:4b on
    # commodity hardware timed out on every planning attempt for a moderately complex
    # multi-step goal (research + report + draft), burning all 3 plan_validation
    # retries without ever producing a plan. 240s gives a local model realistic room
    # to think through a non-trivial goal.
    llm_request_timeout_seconds: int = 240

    # --- Agent execution limits (never allow unbounded loops) ---
    max_tasks_per_run: int = 25
    max_retries_per_task: int = 3
    max_replanning_attempts: int = 3
    max_plan_validation_attempts: int = 3
    max_run_duration_seconds: int = 1800
    max_tool_calls_per_run: int = 100

    # --- Approvals ---
    approval_ttl_seconds: int = 900

    # --- Web research ---
    search_provider: str = "duckduckgo"

    # --- Browser automation ---
    # Comma-separated in the environment (not JSON) for ease of editing in .env.
    browser_allowed_domains_raw: str = ""
    browser_headless: bool = False

    @property
    def browser_allowed_domains(self) -> list[str]:
        return [d.strip() for d in self.browser_allowed_domains_raw.split(",") if d.strip()]

    # --- Python execution runner ---
    python_runner_base_url: str = "http://localhost:8100"
    python_runner_timeout_seconds: int = 60
    python_runner_memory_limit_mb: int = 512
    python_runner_cpu_limit: float = 1.0

    def resolved_workspace_root(self) -> Path:
        return self.workspace_root.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
