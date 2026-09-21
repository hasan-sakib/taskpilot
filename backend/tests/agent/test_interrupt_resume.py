import pytest
from sqlalchemy import select

from app.agent.graph.approvals import ApprovalResolutionError, resolve_approval
from app.agent.graph.runner import is_paused, run_graph
from app.agent.llm.base import PlanResponse, PlanTaskSpec
from app.agent.llm.test_provider import ScriptedTestProvider
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.approval_request import ApprovalRequest
from app.db.models.enums import ApprovalStatus, RunStatus, TaskStatus
from app.db.models.tool_execution import ToolExecution
from tests.agent.helpers import create_run


@pytest.mark.asyncio
async def test_approval_required_tool_pauses_then_resumes_on_approve(
    agent_session_factory, make_deps, workspace_root
):
    initial_state = await create_run(
        agent_session_factory,
        run_id="run-approve",
        goal="Write a note",
        workspace_root=str(workspace_root),
    )
    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="Write a note",
                        tool_name="workspace.write_file",
                        tool_args={"path": "note.txt", "content": "hello world"},
                    )
                ]
            )
        ],
        report="Wrote the note.",
    )
    deps = make_deps(provider)

    paused_result = await run_graph("run-approve", initial_state, deps)
    assert is_paused(paused_result)

    async with agent_session_factory() as session:
        approvals = list(
            await session.scalars(
                select(ApprovalRequest).where(ApprovalRequest.run_id == "run-approve")
            )
        )
        assert len(approvals) == 1
        assert approvals[0].status == ApprovalStatus.PENDING
        approval_id = approvals[0].id

        executions = list(
            await session.scalars(
                select(ToolExecution).where(ToolExecution.run_id == "run-approve")
            )
        )
        assert len(executions) == 0, "tool must not run before approval"

        run = await session.get(AgentRun, "run-approve")
        assert run.status == RunStatus.PAUSED_FOR_APPROVAL

        # Full task-lifecycle checkpoint: at a genuine pause, the task is DB-observable
        # mid-flight (unlike every other transition, which happens synchronously inside
        # one run_graph()/resolve_approval() call and can only be asserted before/after).
        task = (
            await session.scalars(
                select(AgentTask).where(AgentTask.run_id == "run-approve")
            )
        ).one()
        assert task.status == TaskStatus.BLOCKED_ON_APPROVAL

    final_result = await resolve_approval(approval_id, "approved", deps)

    assert not is_paused(final_result)
    assert final_result["status"] == RunStatus.COMPLETED
    assert (workspace_root / "note.txt").read_text() == "hello world"

    async with agent_session_factory() as session:
        task = (
            await session.scalars(
                select(AgentTask).where(AgentTask.run_id == "run-approve")
            )
        ).one()
        assert task.status == TaskStatus.COMPLETED  # blocked_on_approval -> completed
        # The duplicate-execution-prevention invariant: exactly one ToolExecution row,
        # even though this run passed through permission_evaluation twice (once to
        # request approval, once on replay after resume).
        executions = list(
            await session.scalars(
                select(ToolExecution).where(ToolExecution.run_id == "run-approve")
            )
        )
        assert len(executions) == 1

        approval = await session.get(ApprovalRequest, approval_id)
        assert approval.status == ApprovalStatus.APPROVED
        assert approval.resolved_at is not None


@pytest.mark.asyncio
async def test_rejected_approval_fails_task_without_running_tool(
    agent_session_factory, make_deps, workspace_root
):
    initial_state = await create_run(
        agent_session_factory,
        run_id="run-reject",
        goal="Write a note",
        workspace_root=str(workspace_root),
    )
    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="Write a note",
                        tool_name="workspace.write_file",
                        tool_args={"path": "rejected.txt", "content": "nope"},
                    )
                ]
            ),
            PlanResponse(tasks=[]),
        ],
        report="Could not complete the goal.",
    )
    deps = make_deps(provider)

    paused_result = await run_graph("run-reject", initial_state, deps)
    assert is_paused(paused_result)

    async with agent_session_factory() as session:
        approval = (
            await session.scalars(
                select(ApprovalRequest).where(ApprovalRequest.run_id == "run-reject")
            )
        ).one()

    final_result = await resolve_approval(approval.id, "rejected", deps)

    assert not (workspace_root / "rejected.txt").exists()
    assert final_result["status"] == RunStatus.FAILED

    async with agent_session_factory() as session:
        executions = list(
            await session.scalars(
                select(ToolExecution).where(ToolExecution.run_id == "run-reject")
            )
        )
        assert len(executions) == 0, "a rejected action must never run"

        approval_after = await session.get(ApprovalRequest, approval.id)
        assert approval_after.status == ApprovalStatus.REJECTED

        first_task = await session.get(AgentTask, approval.task_id)
        assert first_task.status == TaskStatus.FAILED
        assert first_task.error_message == "Rejected by approval"


@pytest.mark.asyncio
async def test_resolving_already_resolved_approval_raises(
    agent_session_factory, make_deps, workspace_root
):
    initial_state = await create_run(
        agent_session_factory,
        run_id="run-double-resolve",
        goal="Write a note",
        workspace_root=str(workspace_root),
    )
    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="Write a note",
                        tool_name="workspace.write_file",
                        tool_args={"path": "note.txt", "content": "x"},
                    )
                ]
            )
        ],
        report="Done.",
    )
    deps = make_deps(provider)
    await run_graph("run-double-resolve", initial_state, deps)

    async with agent_session_factory() as session:
        approval = (
            await session.scalars(
                select(ApprovalRequest).where(ApprovalRequest.run_id == "run-double-resolve")
            )
        ).one()

    await resolve_approval(approval.id, "approved", deps)

    with pytest.raises(ApprovalResolutionError):
        await resolve_approval(approval.id, "approved", deps)
