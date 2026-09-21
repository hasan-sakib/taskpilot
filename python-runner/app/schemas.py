from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    execution_id: str
    script: str
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    memory_limit_mb: int = Field(default=256, ge=16, le=2048)
    cpu_limit: float = Field(default=1.0, gt=0, le=4)


class ExecuteResponse(BaseModel):
    execution_id: str
    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool
