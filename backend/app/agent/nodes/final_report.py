from collections.abc import Awaitable, Callable

from sqlalchemy import select

from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState
from app.agent.llm.base import LLMProviderError, ReportRequest
from app.agent.nodes._context import NodeContext
from app.db.base import utcnow
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.enums import RunStatus, TaskStatus

_TERMINAL_RUN_STATUSES = {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}


def make(deps: GraphDependencies) -> Callable[[AgentState], Awaitable[dict]]:
    async def final_report_generation(state: AgentState) -> dict:
        run_id = state["run_id"]

        async with deps.session_factory() as session:
            ctx = NodeContext(session, run_id, "final_report_generation")
            run = await session.get(AgentRun, run_id)
            assert run is not None

            if state.get("clarification_needed"):
                report_text = (
                    "The submitted goal could not be validated: "
                    f"{run.error_message or 'goal is empty or too long'}"
                )
                final_status = RunStatus.FAILED
            else:
                plan_version = state.get("plan_version", 0)
                tasks = list(
                    await session.scalars(
                        select(AgentTask)
                        .where(AgentTask.run_id == run_id, AgentTask.plan_version == plan_version)
                        .order_by(AgentTask.sequence_index)
                    )
                )
                summaries = [
                    f"{t.description}: {t.status.value}"
                    + (f" -- {t.error_message}" if t.error_message else "")
                    for t in tasks
                ]
                overall_success = bool(tasks) and all(
                    t.status == TaskStatus.COMPLETED for t in tasks
                )
                final_status = state.get("status") or (
                    RunStatus.COMPLETED if overall_success else RunStatus.FAILED
                )
                if final_status not in _TERMINAL_RUN_STATUSES:
                    final_status = RunStatus.COMPLETED if overall_success else RunStatus.FAILED

                if not tasks:
                    # No task was ever created for this run (planning/plan-validation
                    # never produced a usable plan) -- there is nothing real for a
                    # report-writing LLM call to summarize. Asking it to anyway
                    # invites confabulation: observed in practice, a local model given
                    # a goal and zero grounding facts will write a plausible-sounding
                    # narrative about research it never actually performed. Build a
                    # deterministic report from the actual validation errors instead.
                    validation_errors = state.get("plan_validation_errors") or []
                    if validation_errors:
                        joined = "\n".join(f"- {e}" for e in validation_errors)
                        report_text = (
                            "No plan could be validated for this goal, so no tasks were "
                            f"run.\n\nValidation errors:\n{joined}"
                        )
                    else:
                        report_text = (
                            "No tasks were ever created for this run, so nothing was "
                            "executed."
                        )
                else:
                    try:
                        report_text = await deps.llm_provider.generate_report(
                            ReportRequest(
                                goal=state["goal"],
                                task_summaries=summaries,
                                overall_success=overall_success,
                            )
                        )
                    except LLMProviderError as exc:
                        joined = "\n".join(f"- {s}" for s in summaries)
                        report_text = (
                            f"Report generation failed ({exc}).\n\nTask outcomes:\n{joined}"
                        )

            run.final_report = report_text
            run.status = final_status
            run.completed_at = utcnow()
            await ctx.log_event("final_report_generated", payload={"status": final_status.value})
            await session.commit()

        return {"final_report": report_text, "status": final_status}

    return final_report_generation
