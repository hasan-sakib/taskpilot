from app.agent.graph.deps import GraphDependencies
from app.agent.llm.factory import get_llm_provider
from app.agent.tools.registry import build_default_registry
from app.core.config import Settings
from app.db.models.agent_run import AgentRun


def build_graph_dependencies(settings: Settings, provider_name: str) -> GraphDependencies:
    return GraphDependencies(
        llm_provider=get_llm_provider(provider_name),
        tool_registry=build_default_registry(),
        settings=settings,
    )


def provider_name_for_run(run: AgentRun) -> str:
    """The AgentRun.test_mode flag is what lets a paused run be resumed (a separate
    HTTP request, with no access to the original request body) with the SAME LLM
    provider it was started with."""
    return "test" if run.test_mode else "ollama"
