from pydantic import BaseModel, Field

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext


class ListDirInput(BaseModel):
    path: str = Field(default=".", description="Directory path relative to the workspace root")


class WorkspaceEntry(BaseModel):
    name: str
    is_dir: bool
    size_bytes: int


class ListDirOutput(BaseModel):
    path: str
    entries: list[WorkspaceEntry]


class ListDirTool(Tool):
    name = "workspace.list_dir"
    category = ToolCategory.WORKSPACE
    description = "List files and folders in a workspace directory."
    input_schema = ListDirInput
    output_schema = ListDirOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: ListDirInput, ctx: ToolRunContext) -> ListDirOutput:
        target = resolve_workspace_path(ctx.workspace_root, args.path)
        if not target.exists():
            raise ToolError(f"Directory does not exist: {args.path}")
        if not target.is_dir():
            raise ToolError(f"Not a directory: {args.path}")

        entries = [
            WorkspaceEntry(
                name=child.name,
                is_dir=child.is_dir(),
                size_bytes=child.stat().st_size if child.is_file() else 0,
            )
            for child in sorted(target.iterdir(), key=lambda p: p.name)
        ]
        return ListDirOutput(path=args.path, entries=entries)
