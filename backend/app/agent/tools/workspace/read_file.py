from pydantic import BaseModel, Field

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext

MAX_READ_BYTES = 1_000_000  # 1 MB; large files should be summarized, not dumped whole


class ReadFileInput(BaseModel):
    path: str = Field(description="File path relative to the workspace root")


class ReadFileOutput(BaseModel):
    path: str
    content: str
    truncated: bool
    size_bytes: int


class ReadFileTool(Tool):
    name = "workspace.read_file"
    category = ToolCategory.WORKSPACE
    description = "Read a text file's contents from the workspace."
    input_schema = ReadFileInput
    output_schema = ReadFileOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: ReadFileInput, ctx: ToolRunContext) -> ReadFileOutput:
        target = resolve_workspace_path(ctx.workspace_root, args.path)
        if not target.exists():
            raise ToolError(f"File does not exist: {args.path}")
        if not target.is_file():
            raise ToolError(f"Not a file: {args.path}")

        size_bytes = target.stat().st_size
        try:
            raw = target.read_bytes()[:MAX_READ_BYTES]
            content = raw.decode("utf-8", errors="replace")
        except OSError as exc:
            raise ToolError(f"Could not read file: {exc}") from exc

        return ReadFileOutput(
            path=args.path,
            content=content,
            truncated=size_bytes > MAX_READ_BYTES,
            size_bytes=size_bytes,
        )
