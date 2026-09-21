from datetime import datetime

from pydantic import BaseModel

from app.db.models.enums import EventSeverity


class AgentEventResponse(BaseModel):
    id: str
    run_id: str
    task_id: str | None
    event_type: str
    node_name: str | None
    payload: dict
    severity: EventSeverity
    created_at: datetime

    model_config = {"from_attributes": True}
