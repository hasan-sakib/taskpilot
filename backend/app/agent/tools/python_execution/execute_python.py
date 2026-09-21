from pydantic import BaseModel, Field

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.execution.runner_client import PythonRunnerClient, PythonRunnerError


class ExecutePythonInput(BaseModel):
    script: str
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    memory_limit_mb: int = Field(default=256, ge=16, le=2048)
    cpu_limit: float = Field(default=1.0, gt=0, le=4)


class ExecutePythonOutput(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int


class ExecutePythonTool(Tool):
    name = "python.execute"
    category = ToolCategory.PYTHON_EXECUTION
    description = (
        "Run a Python script in an isolated, network-disabled sandbox container. "
        "Returns stdout, stderr, and the exit code -- a non-zero exit code is not "
        "itself a tool failure, just information about what the script did."
    )
    input_schema = ExecutePythonInput
    output_schema = ExecutePythonOutput
    # Per the project's security model: script execution always requires approval,
    # bound to the exact script content via the same payload_hash every other
    # approval-required tool uses (task.tool_args, which includes `script`, is hashed
    # in full -- editing the script after approval produces a different hash and a
    # fresh, unresolved approval request).
    default_permission = PermissionLevel.REQUIRES_APPROVAL
    # Comfortably above the largest allowed script timeout_seconds (300s) so the HTTP
    # call to the supervisor is never the thing that times out first.
    timeout_seconds = 330

    async def run(self, args: ExecutePythonInput, ctx: ToolRunContext) -> ExecutePythonOutput:
        client = PythonRunnerClient(base_url=ctx.settings.python_runner_base_url)
        try:
            result = await client.execute(
                execution_id=ctx.execution_id,
                script=args.script,
                timeout_seconds=args.timeout_seconds,
                memory_limit_mb=args.memory_limit_mb,
                cpu_limit=args.cpu_limit,
            )
        except PythonRunnerError as exc:
            raise ToolError(f"Python sandbox is currently unavailable: {exc}") from exc

        if result.get("timed_out"):
            raise ToolError(
                f"Script timed out after {args.timeout_seconds}s. "
                f"Partial stdout: {result.get('stdout', '')[:500]!r}"
            )

        return ExecutePythonOutput(
            stdout=result["stdout"],
            stderr=result["stderr"],
            exit_code=result["exit_code"],
            duration_ms=result["duration_ms"],
        )
