from datetime import datetime

from pydantic import BaseModel

from app.db.models.enums import TaskStatus


class TaskDependencyResponse(BaseModel):
    depends_on_task_id: str

    model_config = {"from_attributes": True}


class AgentTaskResponse(BaseModel):
    id: str
    run_id: str
    plan_version: int
    sequence_index: int
    description: str
    tool_name: str
    tool_args: dict
    status: TaskStatus
    priority: int
    deadline: str | None
    retry_count: int
    result_summary: str | None
    error_message: str | None
    parent_task_id: str | None
    dependencies: list[TaskDependencyResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
