from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.db.models.enums import RunStatus


class CreateRunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)
    llm_provider: Literal["ollama", "test"] | None = None


class RunResponse(BaseModel):
    id: str
    goal: str
    status: RunStatus
    plan_version: int
    model_name: str | None
    final_report: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}
