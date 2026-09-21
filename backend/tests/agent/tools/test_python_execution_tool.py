import pytest

from app.agent.tools.base import PermissionLevel, ToolError
from app.agent.tools.python_execution.execute_python import ExecutePythonInput, ExecutePythonTool
from app.execution.runner_client import PythonRunnerError


class _FakeRunnerClient:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.calls = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


@pytest.fixture
def patch_runner_client(monkeypatch):
    def _patch(fake_client):
        monkeypatch.setattr(
            "app.agent.tools.python_execution.execute_python.PythonRunnerClient",
            lambda base_url: fake_client,
        )

    return _patch


@pytest.mark.asyncio
async def test_execute_python_returns_output(run_ctx, patch_runner_client):
    fake = _FakeRunnerClient(
        response={
            "stdout": "hi\n",
            "stderr": "",
            "exit_code": 0,
            "duration_ms": 42,
            "timed_out": False,
        }
    )
    patch_runner_client(fake)

    out = await ExecutePythonTool().run(ExecutePythonInput(script="print('hi')"), run_ctx)
    assert out.stdout == "hi\n"
    assert out.exit_code == 0
    assert fake.calls[0]["execution_id"] == run_ctx.execution_id
    assert fake.calls[0]["script"] == "print('hi')"


@pytest.mark.asyncio
async def test_execute_python_nonzero_exit_is_not_a_tool_error(run_ctx, patch_runner_client):
    fake = _FakeRunnerClient(
        response={
            "stdout": "",
            "stderr": "boom\n",
            "exit_code": 1,
            "duration_ms": 10,
            "timed_out": False,
        }
    )
    patch_runner_client(fake)

    out = await ExecutePythonTool().run(
        ExecutePythonInput(script="import sys; sys.exit(1)"), run_ctx
    )
    assert out.exit_code == 1
    assert out.stderr == "boom\n"


@pytest.mark.asyncio
async def test_execute_python_timeout_raises_tool_error(run_ctx, patch_runner_client):
    fake = _FakeRunnerClient(
        response={
            "stdout": "partial",
            "stderr": "",
            "exit_code": None,
            "duration_ms": 30000,
            "timed_out": True,
        }
    )
    patch_runner_client(fake)

    with pytest.raises(ToolError):
        await ExecutePythonTool().run(
            ExecutePythonInput(script="import time; time.sleep(999)"), run_ctx
        )


@pytest.mark.asyncio
async def test_execute_python_supervisor_unreachable_raises_tool_error(
    run_ctx, patch_runner_client
):
    patch_runner_client(_FakeRunnerClient(error=PythonRunnerError("connection refused")))

    with pytest.raises(ToolError):
        await ExecutePythonTool().run(ExecutePythonInput(script="print(1)"), run_ctx)


def test_execute_python_requires_approval_by_default():
    assert ExecutePythonTool.default_permission == PermissionLevel.REQUIRES_APPROVAL
    decision = ExecutePythonTool().evaluate_permission({}, {})
    assert decision.requires_approval is True


def test_execute_python_input_schema_bounds_are_enforced():
    with pytest.raises(ValueError):
        ExecutePythonInput(script="x", timeout_seconds=99999)
    with pytest.raises(ValueError):
        ExecutePythonInput(script="x", memory_limit_mb=1)
