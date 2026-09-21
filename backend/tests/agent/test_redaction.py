from pydantic import BaseModel

from app.agent.tools.base import Tool, ToolCategory, ToolRunContext


class _EmptyInput(BaseModel):
    pass


class _EmptyOutput(BaseModel):
    pass


class _PlainTool(Tool):
    name = "test.plain_tool"
    category = ToolCategory.WORKSPACE
    description = "d"
    input_schema = _EmptyInput
    output_schema = _EmptyOutput

    async def run(self, args: _EmptyInput, ctx: ToolRunContext) -> _EmptyOutput:
        return _EmptyOutput()


def test_redacts_top_level_secret_like_keys():
    args = {"path": "a.txt", "password": "hunter2", "api_key": "sk-abc123"}
    redacted = _PlainTool().redact_for_audit(args)
    assert redacted["path"] == "a.txt"
    assert redacted["password"] == "***REDACTED***"
    assert redacted["api_key"] == "***REDACTED***"


def test_redacts_nested_secret_like_keys():
    args = {"config": {"auth_token": "secret-value", "timeout": 30}}
    redacted = _PlainTool().redact_for_audit(args)
    assert redacted["config"]["auth_token"] == "***REDACTED***"
    assert redacted["config"]["timeout"] == 30


def test_redacts_secret_like_keys_inside_lists():
    args = {"items": [{"credential": "abc"}, {"name": "ok"}]}
    redacted = _PlainTool().redact_for_audit(args)
    assert redacted["items"][0]["credential"] == "***REDACTED***"
    assert redacted["items"][1]["name"] == "ok"


def test_does_not_redact_non_secret_keys():
    args = {"script": "print('hello')", "content": "some content", "url": "https://x.com"}
    redacted = _PlainTool().redact_for_audit(args)
    assert redacted == args


def test_does_not_redact_non_string_values_even_with_secret_like_key():
    # A non-string "token" (e.g. an integer id, or a bool flag) isn't a leaked
    # credential -- only string values under a secret-like key get masked.
    args = {"token_count": 5}
    redacted = _PlainTool().redact_for_audit(args)
    assert redacted["token_count"] == 5
