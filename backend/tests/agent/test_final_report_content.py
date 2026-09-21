import pytest

from app.agent.llm.test_provider import ScriptedTestProvider
from app.agent.nodes import final_report
from app.db.models.agent_task import AgentTask
from app.db.models.enums import RunStatus, TaskStatus
from tests.agent.helpers import create_run


@pytest.mark.asyncio
async def test_final_report_reflects_a_mix_of_completed_failed_and_skipped_tasks(
    agent_session_factory, make_deps, workspace_root
):
    """Regression coverage for a real gap: the zero-tasks confabulation fix
    (test_final_report_no_tasks.py) is well covered, but nothing previously asserted
    that generate_report() is actually called with task_summaries reflecting each
    task's real outcome. Calls the final_report node directly against a hand-seeded
    mix of task outcomes at a fixed plan_version, rather than driving the full graph
    through a real replanning/exhaustion cycle to reach this state.

    This isn't just a convenient shortcut -- it's a faithful reproduction of a real,
    reachable graph path: a failed task forces replanning only *while*
    replanning_count < max_replanning_attempts (route_completion_evaluation); once
    attempts are exhausted, replanning.py sets status=FAILED WITHOUT incrementing
    plan_version and routes straight to final_report_generation at that same,
    unchanged plan_version -- exactly the state constructed here.
    """
    run_id = "run-mixed-outcomes"
    initial_state = await create_run(
        agent_session_factory,
        run_id=run_id,
        goal="Do three things",
        workspace_root=str(workspace_root),
    )

    async with agent_session_factory() as session:
        session.add_all(
            [
                AgentTask(
                    run_id=run_id,
                    plan_version=1,
                    sequence_index=0,
                    description="List the workspace",
                    tool_name="workspace.list_dir",
                    tool_args={"path": "."},
                    status=TaskStatus.COMPLETED,
                ),
                AgentTask(
                    run_id=run_id,
                    plan_version=1,
                    sequence_index=1,
                    description="Read a file that turned out not to exist",
                    tool_name="workspace.read_file",
                    tool_args={"path": "missing.txt"},
                    status=TaskStatus.FAILED,
                    error_message="No such file: missing.txt",
                ),
                AgentTask(
                    run_id=run_id,
                    plan_version=1,
                    sequence_index=2,
                    description="A task that was no longer needed",
                    tool_name="workspace.create_dir",
                    tool_args={"path": "unused"},
                    status=TaskStatus.SKIPPED,
                ),
            ]
        )
        await session.commit()

    scripted_provider = ScriptedTestProvider(report="Two of three tasks succeeded.")
    deps = make_deps(scripted_provider)

    state = dict(initial_state)
    state["plan_version"] = 1

    node = final_report.make(deps)
    result = await node(state)

    assert result["status"] == RunStatus.FAILED  # not every task completed
    assert result["final_report"] == "Two of three tasks succeeded."

    assert len(scripted_provider.report_requests) == 1
    request = scripted_provider.report_requests[0]
    assert request.goal == "Do three things"
    assert request.overall_success is False
    assert request.task_summaries == [
        "List the workspace: completed",
        "Read a file that turned out not to exist: failed -- No such file: missing.txt",
        "A task that was no longer needed: skipped",
    ]
