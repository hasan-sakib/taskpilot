from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.llm.base import LLMProvider
from app.agent.tools.registry import ToolRegistry
from app.core.config import Settings


def _default_session_factory() -> Callable[[], AsyncSession]:
    from app.db.session import SessionLocal

    return SessionLocal


@dataclass(frozen=True)
class GraphDependencies:
    """Bundles everything a node closure needs, injected at graph-build time.

    Never put an LLMProvider or ToolRegistry instance into AgentState itself --
    LangGraph's checkpointer serializes state, and neither is (or should be) picklable
    checkpoint data.

    session_factory defaults to the global app SessionLocal, but tests inject an
    isolated in-memory one so a graph run never touches the real dev database file.
    """

    llm_provider: LLMProvider
    tool_registry: ToolRegistry
    settings: Settings
    session_factory: Callable[[], AsyncSession] = field(default_factory=_default_session_factory)
