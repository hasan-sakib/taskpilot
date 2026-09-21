from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.db.models.enums import ApprovalStatus


class ApprovalResponse(BaseModel):
    id: str
    run_id: str
    task_id: str
    action_type: str
    target: str | None
    action_payload: dict
    payload_hash: str
    status: ApprovalStatus
    requested_at: datetime
    expires_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    rejection_reason: str | None

    model_config = {"from_attributes": True}


class ResolveApprovalRequest(BaseModel):
    resolved_by: str | None = None
    rejection_reason: str | None = None


ApprovalDecisionLiteral = Literal["approved", "rejected"]
