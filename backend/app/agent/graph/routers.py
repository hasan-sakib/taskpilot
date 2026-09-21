"""Conditional-edge routing functions, kept pure and separate from node bodies so each
one is independently unit-testable against synthetic state (no DB, no LangGraph needed).
"""

from app.agent.graph.state import AgentState
from app.db.models.enums import RunStatus


def route_goal_validation(state: AgentState) -> str:
    return "planning" if state.get("goal_validated") else "final_report_generation"


def route_plan_validation(state: AgentState) -> str:
    errors = state.get("plan_validation_errors") or []
    if not errors:
        return "task_selection"
    attempts = state.get("plan_validation_attempts", 0)
    max_attempts = state.get("max_plan_validation_attempts", 3)
    if attempts < max_attempts:
        return "planning"
    return "final_report_generation"


def route_task_selection(state: AgentState) -> str:
    outcome = state.get("task_selection_outcome")
    return {
        "runnable": "permission_evaluation",
        "blocked": "replanning",
        "all_done": "completion_evaluation",
        "limit_exceeded": "final_report_generation",
        "cancelled": "final_report_generation",
    }[outcome]


def route_permission_evaluation(state: AgentState) -> str:
    if state.get("approval_decision") == "rejected":
        return "retry_recovery"
    return "tool_execution"


def route_result_verification(state: AgentState) -> str:
    result = state.get("last_tool_result")
    if result is None:
        success = False
    elif hasattr(result, "success"):
        success = bool(result.success)
    else:
        success = bool(result.get("success"))
    return "task_selection" if success else "retry_recovery"


def route_retry_recovery(state: AgentState) -> str:
    return "tool_execution" if state.get("retry_recovery_outcome") == "retry" else "replanning"


def route_completion_evaluation(state: AgentState) -> str:
    if state.get("completion_outcome") == "more_work":
        return "replanning"
    return "final_report_generation"


def route_replanning(state: AgentState) -> str:
    if state.get("status") == RunStatus.FAILED:
        return "final_report_generation"
    return "plan_validation"
