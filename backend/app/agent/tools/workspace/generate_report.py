import re

from pydantic import BaseModel

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext

REPORTS_DIR = "reports"


class GenerateReportInput(BaseModel):
    title: str
    content: str
    filename: str | None = None
    overwrite: bool = False


class GenerateReportOutput(BaseModel):
    path: str
    bytes_written: int


class GenerateReportTool(Tool):
    name = "workspace.generate_report"
    category = ToolCategory.WORKSPACE
    description = "Write a Markdown report into the workspace's reports/ folder."
    input_schema = GenerateReportInput
    output_schema = GenerateReportOutput
    # A purpose-built write into the dedicated reports/ location for a core, expected
    # agent capability -- unlike the general-purpose workspace.write_file (which can
    # target any path and defaults to requiring approval), this is auto-approved.
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(self, args: GenerateReportInput, ctx: ToolRunContext) -> GenerateReportOutput:
        filename = args.filename or f"{_slugify(args.title)}.md"
        if not filename.endswith(".md"):
            filename += ".md"

        relative_path = f"{REPORTS_DIR}/{filename}"
        target = resolve_workspace_path(ctx.workspace_root, relative_path)
        if target.exists() and not args.overwrite:
            raise ToolError(f"Report already exists (overwrite=False): {relative_path}")

        target.parent.mkdir(parents=True, exist_ok=True)
        body = f"# {args.title}\n\n{args.content}\n"

        tmp_path = target.with_name(target.name + ".tmp")
        tmp_path.write_text(body, encoding="utf-8")
        tmp_path.replace(target)

        return GenerateReportOutput(path=relative_path, bytes_written=len(body.encode("utf-8")))


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "report"
