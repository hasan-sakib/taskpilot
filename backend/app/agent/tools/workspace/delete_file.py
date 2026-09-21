import shutil

from pydantic import BaseModel

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext


class DeleteFileInput(BaseModel):
    path: str


class DeleteFileOutput(BaseModel):
    path: str
    was_directory: bool


class DeleteFileTool(Tool):
    name = "workspace.delete_file"
    category = ToolCategory.WORKSPACE
    description = "Delete a file or directory from the workspace."
    input_schema = DeleteFileInput
    output_schema = DeleteFileOutput
    # Explicit default-approval-required action per the project's security model --
    # deletion is destructive and irreversible from the agent's side.
    default_permission = PermissionLevel.REQUIRES_APPROVAL
    timeout_seconds = 10

    async def run(self, args: DeleteFileInput, ctx: ToolRunContext) -> DeleteFileOutput:
        target = resolve_workspace_path(ctx.workspace_root, args.path)
        if target == ctx.workspace_root.resolve():
            raise ToolError("Refusing to delete the workspace root itself")
        if not target.exists():
            raise ToolError(f"Path does not exist: {args.path}")

        was_directory = target.is_dir()
        if was_directory:
            shutil.rmtree(target)
        else:
            target.unlink()

        return DeleteFileOutput(path=args.path, was_directory=was_directory)
