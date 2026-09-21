from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.graph.state import AgentState, build_initial_state
from app.db.models.agent_run import AgentRun
from app.db.models.enums import RunStatus


async def create_run(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    run_id: str,
    goal: str,
    workspace_root: str,
) -> AgentState:
    async with session_factory() as session:
        session.add(
            AgentRun(
                id=run_id,
                goal=goal,
                status=RunStatus.PENDING,
                workspace_root=workspace_root,
            )
        )
        await session.commit()

    return build_initial_state(
        run_id=run_id, goal=goal, workspace_root=workspace_root, llm_provider="test"
    )
