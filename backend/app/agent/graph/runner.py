from typing import Any

from langgraph.types import Command

from app.agent.graph.builder import compile_graph
from app.agent.graph.checkpointer import get_checkpointer
from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState


async def run_graph(run_id: str, initial_state: AgentState, deps: GraphDependencies) -> dict:
    checkpoint_path = str(deps.settings.checkpoint_db_path)
    config = {"configurable": {"thread_id": run_id}}
    async with get_checkpointer(checkpoint_path) as checkpointer:
        graph = compile_graph(deps, checkpointer)
        return await graph.ainvoke(initial_state, config=config)


async def resume_graph(run_id: str, resume_value: dict[str, Any], deps: GraphDependencies) -> dict:
    checkpoint_path = str(deps.settings.checkpoint_db_path)
    config = {"configurable": {"thread_id": run_id}}
    async with get_checkpointer(checkpoint_path) as checkpointer:
        graph = compile_graph(deps, checkpointer)
        return await graph.ainvoke(Command(resume=resume_value), config=config)


def is_paused(result: dict) -> bool:
    return "__interrupt__" in result
