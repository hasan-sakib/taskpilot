from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from app.db.models.enums import RunStatus, TaskStatus


class PlanTask(BaseModel):
    """The graph-state mirror of an AgentTask row."""

    task_id: str
    sequence_index: int
    description: str
    tool_name: str
    tool_args: dict = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0


class ToolCallRequest(BaseModel):
    tool_name: str
    args: dict = Field(default_factory=dict)
    target: str | None = None
    payload_hash: str
    requires_approval: bool


class ToolResult(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None
    duration_ms: int | None = None
    exit_code: int | None = None


ApprovalDecision = Literal["approved", "rejected"]

TaskSelectionOutcome = Literal["runnable", "blocked", "all_done", "limit_exceeded", "cancelled"]
RetryRecoveryOutcome = Literal["retry", "exhausted"]
CompletionOutcome = Literal["done", "more_work"]


class AgentState(TypedDict, total=False):
    run_id: str
    goal: str
    goal_validated: bool
    clarification_needed: bool

    plan: list[PlanTask]
    plan_version: int
    plan_validation_errors: list[str]
    plan_validation_attempts: int

    current_task_id: str | None
    task_selection_outcome: TaskSelectionOutcome | None

    current_tool_call: ToolCallRequest | None
    pending_approval_id: str | None
    approval_decision: ApprovalDecision | None

    last_tool_result: ToolResult | None
    retry_recovery_outcome: RetryRecoveryOutcome | None
    completion_outcome: CompletionOutcome | None

    retry_count: int
    max_retries_per_task: int
    replanning_count: int
    max_replanning_attempts: int
    max_plan_validation_attempts: int

    status: RunStatus
    final_report: str | None

    workspace_root: str
    user_preferences_snapshot: dict
    llm_provider: str
    model_name: str | None


def build_initial_state(
    *,
    run_id: str,
    goal: str,
    workspace_root: str,
    llm_provider: str,
    model_name: str | None = None,
    max_retries_per_task: int = 3,
    max_replanning_attempts: int = 3,
    max_plan_validation_attempts: int = 3,
    user_preferences_snapshot: dict | None = None,
) -> AgentState:
    return AgentState(
        run_id=run_id,
        goal=goal,
        goal_validated=False,
        clarification_needed=False,
        plan=[],
        plan_version=0,
        plan_validation_errors=[],
        plan_validation_attempts=0,
        current_task_id=None,
        task_selection_outcome=None,
        current_tool_call=None,
        pending_approval_id=None,
        approval_decision=None,
        last_tool_result=None,
        retry_recovery_outcome=None,
        completion_outcome=None,
        retry_count=0,
        max_retries_per_task=max_retries_per_task,
        replanning_count=0,
        max_replanning_attempts=max_replanning_attempts,
        max_plan_validation_attempts=max_plan_validation_attempts,
        status=RunStatus.PENDING,
        final_report=None,
        workspace_root=workspace_root,
        user_preferences_snapshot=user_preferences_snapshot or {},
        llm_provider=llm_provider,
        model_name=model_name,
    )
