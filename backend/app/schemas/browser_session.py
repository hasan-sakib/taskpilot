from datetime import datetime

from pydantic import BaseModel

from app.db.models.enums import BrowserSessionStatus


class BrowserSessionResponse(BaseModel):
    id: str
    run_id: str
    task_id: str | None
    status: BrowserSessionStatus
    current_url: str | None
    headless: bool
    started_at: datetime | None
    closed_at: datetime | None
    is_live: bool

    model_config = {"from_attributes": True}
