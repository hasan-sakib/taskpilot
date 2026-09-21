from pydantic import BaseModel

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext


class WriteFileInput(BaseModel):
    path: str
    content: str
    overwrite: bool = False


class WriteFileOutput(BaseModel):
    path: str
    bytes_written: int


class WriteFileTool(Tool):
    name = "workspace.write_file"
    category = ToolCategory.WORKSPACE
    description = "Create or overwrite a file in the workspace."
    input_schema = WriteFileInput
    output_schema = WriteFileOutput
    # Writing content the agent decided on is consequential enough to confirm by default;
    # Phase 4 preference wiring may let a user relax this for specific subfolders, but never
    # below what Tool.evaluate_permission's floor allows.
    default_permission = PermissionLevel.REQUIRES_APPROVAL
    timeout_seconds = 10

    async def run(self, args: WriteFileInput, ctx: ToolRunContext) -> WriteFileOutput:
        target = resolve_workspace_path(ctx.workspace_root, args.path)
        if target.exists() and not args.overwrite:
            raise ToolError(f"File already exists (overwrite=False): {args.path}")
        target.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = target.with_name(target.name + ".tmp")
        tmp_path.write_text(args.content, encoding="utf-8")
        tmp_path.replace(target)  # atomic rename on POSIX

        return WriteFileOutput(path=args.path, bytes_written=len(args.content.encode("utf-8")))
