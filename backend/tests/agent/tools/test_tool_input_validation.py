"""Systematic input-validation coverage across every registered tool.

Prior to this file, only 2 of the ~28 registered tools had any test asserting that a
missing required argument is actually rejected -- everything else relied entirely on
Pydantic's automatic enforcement at call time with nothing verifying it. This
parametrizes over the real tool registry so every tool with at least one required
field gets that coverage for free, and stays correct automatically as tools are added.
"""

import pytest
from pydantic import ValidationError

from app.agent.tools.registry import build_default_registry

_TOOLS = build_default_registry().all()
_TOOLS_WITH_REQUIRED_FIELDS = [
    tool
    for tool in _TOOLS
    if any(field.is_required() for field in tool.input_schema.model_fields.values())
]


@pytest.mark.parametrize(
    "tool", _TOOLS_WITH_REQUIRED_FIELDS, ids=[t.name for t in _TOOLS_WITH_REQUIRED_FIELDS]
)
def test_missing_required_fields_are_rejected(tool):
    with pytest.raises(ValidationError):
        tool.input_schema()


@pytest.mark.parametrize("tool", _TOOLS, ids=[t.name for t in _TOOLS])
def test_every_registered_tool_has_a_distinct_name_and_a_description(tool):
    # Cheap sanity check that rides along with the registry iteration above: a tool
    # with an empty description or a name collision would be a real, silent bug (the
    # LLM planner is shown these names/descriptions verbatim to choose from).
    assert tool.name
    assert tool.description
    assert sum(1 for t in _TOOLS if t.name == tool.name) == 1


class TestWrongTypeArguments:
    """One representative wrong-type case per tool category -- missing-field coverage
    above doesn't catch a value of the wrong Python type for a field that IS present."""

    def test_execute_python_rejects_non_string_script(self):
        from app.agent.tools.python_execution.execute_python import ExecutePythonInput

        with pytest.raises(ValidationError):
            ExecutePythonInput(script=12345)

    def test_web_search_rejects_null_query(self):
        from app.agent.tools.web_research.search import WebSearchInput

        with pytest.raises(ValidationError):
            WebSearchInput(query=None)

    def test_navigate_rejects_non_string_url(self):
        from app.agent.tools.browser.navigate import NavigateInput

        with pytest.raises(ValidationError):
            NavigateInput(session_id="s1", url=["not", "a", "url"])

    def test_write_file_rejects_non_string_content(self):
        from app.agent.tools.workspace.write_file import WriteFileInput

        with pytest.raises(ValidationError):
            WriteFileInput(path="a.txt", content={"not": "a string"})

    def test_create_task_rejects_non_dict_tool_args(self):
        from app.agent.tools.task_management.create_task import CreateTaskInput

        with pytest.raises(ValidationError):
            CreateTaskInput(description="d", tool_name="workspace.list_dir", tool_args="not a dict")
