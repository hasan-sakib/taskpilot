from pydantic import BaseModel

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext


class CreateDirInput(BaseModel):
    path: str


class CreateDirOutput(BaseModel):
    path: str
    created: bool


class CreateDirTool(Tool):
    name = "workspace.create_dir"
    category = ToolCategory.WORKSPACE
    description = "Create a directory (and any missing parent directories) in the workspace."
    input_schema = CreateDirInput
    output_schema = CreateDirOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: CreateDirInput, ctx: ToolRunContext) -> CreateDirOutput:
        target = resolve_workspace_path(ctx.workspace_root, args.path)
        if target.exists() and not target.is_dir():
            raise ToolError(f"Path already exists and is not a directory: {args.path}")

        already_existed = target.is_dir()
        target.mkdir(parents=True, exist_ok=True)
        return CreateDirOutput(path=args.path, created=not already_existed)
