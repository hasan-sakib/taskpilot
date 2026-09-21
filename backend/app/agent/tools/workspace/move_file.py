from pydantic import BaseModel

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext


class MoveFileInput(BaseModel):
    source: str
    destination: str
    overwrite: bool = False


class MoveFileOutput(BaseModel):
    source: str
    destination: str


class MoveFileTool(Tool):
    name = "workspace.move_file"
    category = ToolCategory.WORKSPACE
    # Renaming is just a move to a new name in the same directory, so one tool covers
    # both listed capabilities ("rename files" and "move files") without duplicating
    # the same filesystem operation under two names.
    description = "Move or rename a file or directory within the workspace."
    input_schema = MoveFileInput
    output_schema = MoveFileOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: MoveFileInput, ctx: ToolRunContext) -> MoveFileOutput:
        source = resolve_workspace_path(ctx.workspace_root, args.source)
        destination = resolve_workspace_path(ctx.workspace_root, args.destination)

        if not source.exists():
            raise ToolError(f"Source does not exist: {args.source}")
        if destination.exists() and not args.overwrite:
            raise ToolError(f"Destination already exists (overwrite=False): {args.destination}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)

        return MoveFileOutput(source=args.source, destination=args.destination)
