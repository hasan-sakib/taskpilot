from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolRunContext


class _EmptyInput(BaseModel):
    pass


class _EmptyOutput(BaseModel):
    pass


class _AutoTool(Tool):
    name = "test.auto_tool"
    category = ToolCategory.WORKSPACE
    description = "d"
    input_schema = _EmptyInput
    output_schema = _EmptyOutput
    default_permission = PermissionLevel.AUTO

    async def run(self, args: _EmptyInput, ctx: ToolRunContext) -> _EmptyOutput:
        return _EmptyOutput()


class _RequiresApprovalTool(Tool):
    name = "test.requires_approval_tool"
    category = ToolCategory.WORKSPACE
    description = "d"
    input_schema = _EmptyInput
    output_schema = _EmptyOutput
    default_permission = PermissionLevel.REQUIRES_APPROVAL

    async def run(self, args: _EmptyInput, ctx: ToolRunContext) -> _EmptyOutput:
        return _EmptyOutput()


def test_auto_tool_is_auto_with_no_preferences():
    decision = _AutoTool().evaluate_permission({}, {})
    assert decision.requires_approval is False


def test_preference_can_raise_an_auto_tool_to_require_approval():
    prefs = {"tool.test.auto_tool.require_approval": True}
    decision = _AutoTool().evaluate_permission({}, prefs)
    assert decision.requires_approval is True


def test_unrelated_preference_does_not_affect_permission():
    prefs = {"tool.some.other_tool.require_approval": True}
    decision = _AutoTool().evaluate_permission({}, prefs)
    assert decision.requires_approval is False


def test_preference_cannot_lower_a_tool_below_its_default():
    # There is no preference key that means "don't require approval" -- the floor set
    # by default_permission is absolute, never overridden downward by memory.
    prefs = {"tool.test.requires_approval_tool.require_approval": False}
    decision = _RequiresApprovalTool().evaluate_permission({}, prefs)
    assert decision.requires_approval is True


def test_falsy_non_true_preference_value_does_not_trigger_override():
    # Only an explicit `True` triggers the override -- a truthy-but-not-True value
    # (e.g. a stray string) must not silently enable it.
    prefs = {"tool.test.auto_tool.require_approval": "yes"}
    decision = _AutoTool().evaluate_permission({}, prefs)
    assert decision.requires_approval is False
