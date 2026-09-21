import pytest

from app.agent.graph.runner import run_graph
from app.agent.llm.base import PlanResponse
from app.agent.llm.test_provider import ScriptedTestProvider
from app.db.models.enums import RunStatus
from tests.agent.helpers import create_run


@pytest.mark.asyncio
async def test_final_report_does_not_call_the_llm_when_no_tasks_were_ever_created(
    agent_session_factory, make_deps, workspace_root
):
    """Regression test for a real bug found via live integration testing against qwen3:4b:
    when plan validation never succeeds (e.g. every planning attempt times out or the
    model never produces a schema-valid plan), no AgentTask rows ever exist for the run.
    The final-report node used to call generate_report() anyway with an empty
    task_summaries list -- with nothing to ground it, a real local model wrote a
    plausible-sounding narrative describing research it never actually performed
    (specific platforms "searched" that were never touched by any tool call). The fix:
    when there are zero tasks, skip the LLM call entirely and build a deterministic
    report from the actual plan_validation_errors instead.
    """
    initial_state = await create_run(
        agent_session_factory,
        run_id="run-no-tasks",
        goal="Research something and write a report",
        workspace_root=str(workspace_root),
    )
    # Every plan the scripted provider returns has zero tasks, so plan_validation
    # rejects it every attempt ("Plan has no tasks") until attempts are exhausted --
    # exactly the zero-tasks-ever-created scenario this test targets.
    provider = ScriptedTestProvider(plans=[PlanResponse(tasks=[])])
    deps = make_deps(provider)

    result = await run_graph("run-no-tasks", initial_state, deps)

    assert result["status"] == RunStatus.FAILED
    assert provider.report_requests == [], (
        "generate_report() must not be called when no tasks were ever created -- "
        "there is nothing real to ground a report in."
    )
    assert "Plan has no tasks" in result["final_report"]
    assert "No plan could be validated" in result["final_report"]
