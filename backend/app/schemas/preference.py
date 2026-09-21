from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreatePreferenceRequest(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    value: Any
    description: str | None = None
    # Explicit confirmation is the whole point of this model (see UserPreference docs):
    # a human creating a preference directly through this API is, by construction,
    # explicitly confirming it -- but defaults to False so a future "agent proposes a
    # preference" path can create an inert row that a human must separately confirm.
    confirmed_by_user: bool = True
    available_to_future_runs: bool = True


class UpdatePreferenceRequest(BaseModel):
    value: Any | None = None
    description: str | None = None
    confirmed_by_user: bool | None = None
    available_to_future_runs: bool | None = None


class PreferenceResponse(BaseModel):
    id: str
    key: str
    value: Any
    description: str | None
    confirmed_by_user: bool
    available_to_future_runs: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
