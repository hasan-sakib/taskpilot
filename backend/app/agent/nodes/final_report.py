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
                    report_text = f"Report generation failed ({exc}).\n\nTask outcomes:\n{joined}"

            run.final_report = report_text
            run.status = final_status
            run.completed_at = utcnow()
            await ctx.log_event("final_report_generated", payload={"status": final_status.value})
            await session.commit()

        return {"final_report": report_text, "status": final_status}

    return final_report_generation
