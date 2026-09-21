from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AgentEvent,
    AgentRun,
    AgentTask,
    ApprovalRequest,
    TaskDependency,
    ToolExecution,
    UserPreference,
    WorkspaceArtifact,
)
from app.db.models.enums import (
    ApprovalStatus,
    ArtifactType,
    RunStatus,
    TaskStatus,
    ToolExecutionStatus,
)


async def _make_run(session: AsyncSession) -> AgentRun:
    run = AgentRun(goal="Research jobs", status=RunStatus.RUNNING, workspace_root="/workspace")
    session.add(run)
    await session.flush()
    return run


@pytest.mark.asyncio
async def test_create_run_and_task_with_dependency(db_session: AsyncSession) -> None:
    run = await _make_run(db_session)

    task_a = AgentTask(
        run_id=run.id,
        plan_version=1,
        sequence_index=0,
        description="Search for jobs",
        tool_name="web_search",
        tool_args={"query": "AI engineer"},
        status=TaskStatus.PENDING,
    )
    task_b = AgentTask(
        run_id=run.id,
        plan_version=1,
        sequence_index=1,
        description="Write report",
        tool_name="generate_report",
        tool_args={},
        status=TaskStatus.PENDING,
    )
    db_session.add_all([task_a, task_b])
    await db_session.flush()

    dep = TaskDependency(task_id=task_b.id, depends_on_task_id=task_a.id)
    db_session.add(dep)
    await db_session.commit()

    stored = await db_session.scalar(
        select(TaskDependency).where(TaskDependency.task_id == task_b.id)
    )
    assert stored is not None
    assert stored.depends_on_task_id == task_a.id


@pytest.mark.asyncio
async def test_task_plan_sequence_unique_constraint(db_session: AsyncSession) -> None:
    run = await _make_run(db_session)

    db_session.add(
        AgentTask(
            run_id=run.id,
            plan_version=1,
            sequence_index=0,
            description="First",
            tool_name="noop",
            tool_args={},
        )
    )
    await db_session.commit()

    db_session.add(
        AgentTask(
            run_id=run.id,
            plan_version=1,
            sequence_index=0,
            description="Duplicate sequence index",
            tool_name="noop",
            tool_args={},
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_tool_execution_attempt_number_unique_per_task(db_session: AsyncSession) -> None:
    run = await _make_run(db_session)
    task = AgentTask(
        run_id=run.id,
        plan_version=1,
        sequence_index=0,
        description="Run script",
        tool_name="execute_python",
        tool_args={},
    )
    db_session.add(task)
    await db_session.flush()

    db_session.add(
        ToolExecution(
            run_id=run.id,
            task_id=task.id,
            attempt_number=1,
            tool_name="execute_python",
            input_payload={},
            payload_hash="abc123",
            status=ToolExecutionStatus.STARTED,
        )
    )
    await db_session.commit()

    # Simulates a crash-recovery replay: the same (task_id, attempt_number)
    # must be rejected so tool_execution can safely reuse the prior result.
    db_session.add(
        ToolExecution(
            run_id=run.id,
            task_id=task.id,
            attempt_number=1,
            tool_name="execute_python",
            input_payload={},
            payload_hash="abc123",
            status=ToolExecutionStatus.STARTED,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_approval_request_unique_run_task_hash(db_session: AsyncSession) -> None:
    run = await _make_run(db_session)
    task = AgentTask(
        run_id=run.id,
        plan_version=1,
        sequence_index=0,
        description="Send email",
        tool_name="send_email",
        tool_args={},
    )
    db_session.add(task)
    await db_session.flush()

    now = datetime.now(UTC)
    approval = ApprovalRequest(
        run_id=run.id,
        task_id=task.id,
        action_type="send_email",
        target="someone@example.com",
        action_payload={"subject": "hi"},
        payload_hash="hash-1",
        status=ApprovalStatus.PENDING,
        requested_at=now,
        expires_at=now + timedelta(minutes=15),
    )
    db_session.add(approval)
    await db_session.commit()

    # An idempotent upsert (same run/task/payload_hash) must not create a
    # second row — this backs the interrupt-replay safety guarantee.
    duplicate = ApprovalRequest(
        run_id=run.id,
        task_id=task.id,
        action_type="send_email",
        target="someone@example.com",
        action_payload={"subject": "hi"},
        payload_hash="hash-1",
        status=ApprovalStatus.PENDING,
        requested_at=now,
        expires_at=now + timedelta(minutes=15),
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_approval_request_distinct_hash_per_attempt_does_not_collide(
    db_session: AsyncSession,
) -> None:
    # Complements the collision test above: a *different* payload_hash for the same
    # (run_id, task_id) -- exactly what compute_payload_hash's retry_count parameter
    # produces on a second attempt -- must coexist and be independently resolvable.
    # Without this, task.retry on an approval-required task would deadlock the run.
    run = await _make_run(db_session)
    task = AgentTask(
        run_id=run.id,
        plan_version=1,
        sequence_index=0,
        description="Send email",
        tool_name="send_email",
        tool_args={},
    )
    db_session.add(task)
    await db_session.flush()

    now = datetime.now(UTC)
    first_attempt = ApprovalRequest(
        run_id=run.id,
        task_id=task.id,
        action_type="send_email",
        target="someone@example.com",
        action_payload={"subject": "hi"},
        payload_hash="hash-attempt-0",
        status=ApprovalStatus.APPROVED,
        requested_at=now,
        expires_at=now + timedelta(minutes=15),
        resolved_at=now,
    )
    second_attempt = ApprovalRequest(
        run_id=run.id,
        task_id=task.id,
        action_type="send_email",
        target="someone@example.com",
        action_payload={"subject": "hi"},
        payload_hash="hash-attempt-1",
        status=ApprovalStatus.PENDING,
        requested_at=now,
        expires_at=now + timedelta(minutes=15),
    )
    db_session.add_all([first_attempt, second_attempt])
    await db_session.commit()

    assert first_attempt.id != second_attempt.id
    assert second_attempt.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_workspace_artifact_and_event_and_preference(db_session: AsyncSession) -> None:
    run = await _make_run(db_session)

    artifact = WorkspaceArtifact(
        run_id=run.id,
        relative_path="reports/job_report.md",
        artifact_type=ArtifactType.REPORT,
        size_bytes=1024,
        created_by_tool="generate_report",
    )
    event = AgentEvent(
        run_id=run.id,
        event_type="node_entered",
        node_name="planning",
        payload={"detail": "generated plan"},
    )
    preference = UserPreference(
        key="tool.web_research.auto_approve",
        value={"enabled": False},
        confirmed_by_user=True,
    )
    db_session.add_all([artifact, event, preference])
    await db_session.commit()

    assert artifact.id is not None
    assert event.id is not None
    assert preference.id is not None


@pytest.mark.asyncio
async def test_foreign_keys_are_enforced(db_session: AsyncSession) -> None:
    # SQLite ignores FK constraints unless PRAGMA foreign_keys=ON is set per
    # connection; this confirms that pragma is actually taking effect.
    db_session.add(
        AgentTask(
            run_id="does-not-exist",
            plan_version=1,
            sequence_index=0,
            description="Orphan task",
            tool_name="noop",
            tool_args={},
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


@pytest.mark.asyncio
async def test_deleting_run_cascades_to_tasks_and_tool_executions(
    db_session: AsyncSession,
) -> None:
    run = await _make_run(db_session)
    task = AgentTask(
        run_id=run.id,
        plan_version=1,
        sequence_index=0,
        description="Run script",
        tool_name="execute_python",
        tool_args={},
    )
    db_session.add(task)
    await db_session.flush()

    db_session.add(
        ToolExecution(
            run_id=run.id,
            task_id=task.id,
            attempt_number=1,
            tool_name="execute_python",
            input_payload={},
            payload_hash="abc123",
            status=ToolExecutionStatus.STARTED,
        )
    )
    await db_session.commit()

    await db_session.delete(run)
    await db_session.commit()

    assert await db_session.scalar(select(AgentTask).where(AgentTask.id == task.id)) is None
    assert (
        await db_session.scalar(select(ToolExecution).where(ToolExecution.task_id == task.id))
        is None
    )
