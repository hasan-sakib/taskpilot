import asyncio

import pytest
import pytest_asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agent.graph.approvals import ApprovalResolutionError, resolve_approval
from app.agent.graph.deps import GraphDependencies
from app.agent.graph.runner import run_graph
from app.agent.graph.state import build_initial_state
from app.agent.llm.base import PlanResponse, PlanTaskSpec
from app.agent.llm.test_provider import ScriptedTestProvider
from app.agent.tools.registry import build_default_registry
from app.core.config import Settings
from app.db.base import Base, utcnow
from app.db.models.agent_run import AgentRun
from app.db.models.approval_request import ApprovalRequest
from app.db.models.enums import ApprovalStatus, RunStatus
from app.db.sqlite_pragma import configure_sqlite_connection


@pytest_asyncio.fixture
async def file_backed_session_factory(tmp_path):
    """A real file-backed SQLite DB (not :memory:/StaticPool) so two concurrent
    AsyncSession instances get genuinely separate connections -- required to exercise
    an actual race between two resolve_approval calls rather than one that's serialized
    by sharing a single physical connection."""
    db_path = tmp_path / "concurrency_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    configure_sqlite_connection(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    yield session_factory
    await engine.dispose()


async def _seed_paused_run(session_factory, settings, workspace_root, run_id: str) -> str:
    async with session_factory() as session:
        session.add(
            AgentRun(
                id=run_id,
                goal="Write a file",
                status=RunStatus.PENDING,
                workspace_root=str(workspace_root),
                test_mode=True,
            )
        )
        await session.commit()

    provider = ScriptedTestProvider(
        plans=[
            PlanResponse(
                tasks=[
                    PlanTaskSpec(
                        description="Write a.txt",
                        tool_name="workspace.write_file",
                        tool_args={"path": "a.txt", "content": "hi"},
                    )
                ]
            )
        ],
        report="Wrote the file.",
    )
    deps = GraphDependencies(
        llm_provider=provider,
        tool_registry=build_default_registry(),
        settings=settings,
        session_factory=session_factory,
    )
    initial_state = build_initial_state(
        run_id=run_id, goal="Write a file", workspace_root=str(workspace_root), llm_provider="test"
    )
    await run_graph(run_id, initial_state, deps)

    async with session_factory() as session:
        approval = (
            await session.scalars(select(ApprovalRequest).where(ApprovalRequest.run_id == run_id))
        ).first()
        return approval.id


@pytest.mark.asyncio
async def test_concurrent_approve_and_reject_only_one_wins(
    file_backed_session_factory, tmp_path
):
    """Real-timing smoke check: fires genuinely concurrent approve/reject calls and
    confirms the fixed code behaves well (exactly one winner, one clean error). This is
    NOT a reliable regression test on its own -- real asyncio/SQLite scheduling doesn't
    reliably land in the exact race window, so this same assertion can pass even against
    the pre-fix racy implementation by luck. The deterministic regression test below
    (test_a_concurrent_winner_landing_mid_call_is_still_detected) forces the exact
    window and is what actually proves the fix.
    """
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    settings = Settings(data_dir=tmp_path / "data", workspace_root=workspace_root)
    approval_id = await _seed_paused_run(
        file_backed_session_factory, settings, workspace_root, "run-race"
    )

    deps = GraphDependencies(
        llm_provider=ScriptedTestProvider(plans=[], report=""),
        tool_registry=build_default_registry(),
        settings=settings,
        session_factory=file_backed_session_factory,
    )

    results = await asyncio.gather(
        resolve_approval(approval_id, "approved", deps, resolved_by="a"),
        resolve_approval(approval_id, "rejected", deps, resolved_by="b"),
        return_exceptions=True,
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, f"expected exactly one winner, got {results}"
    assert len(failures) == 1
    assert isinstance(failures[0], ApprovalResolutionError)
    assert "not pending" in str(failures[0])

    async with file_backed_session_factory() as session:
        approval = await session.get(ApprovalRequest, approval_id)
        assert approval.status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED)


@pytest.mark.asyncio
async def test_a_concurrent_winner_landing_mid_call_is_still_detected(
    file_backed_session_factory, tmp_path, monkeypatch
):
    """Deterministically forces the exact race window a real concurrent approve/reject
    could hit: another resolver's UPDATE commits in the gap between this call deciding
    to issue its own conditional UPDATE and that UPDATE actually executing. The old
    read-then-write code (session.get() -> Python `if status == PENDING` -> mutate ->
    commit) would miss this entirely, since its status check ran against a snapshot
    read before the sneak-in write landed. The fix closes that gap by making the check
    and the write one atomic `UPDATE ... WHERE status = 'pending'` statement, evaluated
    by SQLite at execute() time -- so even a write landing in this exact gap is caught.
    """
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    settings = Settings(data_dir=tmp_path / "data", workspace_root=workspace_root)
    approval_id = await _seed_paused_run(
        file_backed_session_factory, settings, workspace_root, "run-toctou"
    )

    async def _sneak_in_a_concurrent_approval() -> None:
        async with file_backed_session_factory() as other_session:
            await other_session.execute(
                update(ApprovalRequest)
                .where(
                    ApprovalRequest.id == approval_id,
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                )
                .values(
                    status=ApprovalStatus.APPROVED,
                    resolved_at=utcnow(),
                    resolved_by="sneaky-winner",
                )
            )
            await other_session.commit()

    original_execute = AsyncSession.execute
    injected = False

    async def patched_execute(self, statement, *args, **kwargs):
        nonlocal injected
        if not injected:
            injected = True
            await _sneak_in_a_concurrent_approval()
        return await original_execute(self, statement, *args, **kwargs)

    monkeypatch.setattr(AsyncSession, "execute", patched_execute)

    deps = GraphDependencies(
        llm_provider=ScriptedTestProvider(plans=[], report=""),
        tool_registry=build_default_registry(),
        settings=settings,
        session_factory=file_backed_session_factory,
    )

    with pytest.raises(ApprovalResolutionError, match="not pending"):
        await resolve_approval(approval_id, "rejected", deps, resolved_by="loser")

    monkeypatch.undo()
    async with file_backed_session_factory() as session:
        approval = await session.get(ApprovalRequest, approval_id)
        assert approval.status == ApprovalStatus.APPROVED
        assert approval.resolved_by == "sneaky-winner"
