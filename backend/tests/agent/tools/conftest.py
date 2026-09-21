import pytest

from app.agent.llm.test_provider import ScriptedTestProvider
from app.agent.tools.base import ToolRunContext
from app.agent.tools.registry import build_default_registry


@pytest.fixture
def run_ctx(workspace_root, agent_session_factory, agent_settings) -> ToolRunContext:
    return ToolRunContext(
        workspace_root=workspace_root,
        run_id="test-run",
        task_id="test-task",
        execution_id="test-execution",
        session_factory=agent_session_factory,
        tool_registry=build_default_registry(),
        llm_provider=ScriptedTestProvider(),
        settings=agent_settings,
    )
