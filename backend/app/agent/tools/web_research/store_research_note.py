import re
from datetime import datetime

from pydantic import BaseModel

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext

NOTES_DIR = "research"


class StoreResearchNoteInput(BaseModel):
    title: str
    content: str
    source_url: str | None = None
    filename: str | None = None


class StoreResearchNoteOutput(BaseModel):
    path: str
    bytes_written: int


class StoreResearchNoteTool(Tool):
    name = "web_research.store_research_note"
    category = ToolCategory.WEB_RESEARCH
    description = "Save a research note (with an optional source URL) into the workspace."
    input_schema = StoreResearchNoteInput
    output_schema = StoreResearchNoteOutput
    # A purpose-built write into the dedicated research/ location, core to this tool
    # category's job -- unlike workspace.write_file, auto-approved by default.
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 10

    async def run(
        self, args: StoreResearchNoteInput, ctx: ToolRunContext
    ) -> StoreResearchNoteOutput:
        filename = args.filename or f"{_slugify(args.title)}.md"
        if not filename.endswith(".md"):
            filename += ".md"

        relative_path = f"{NOTES_DIR}/{filename}"
        target = resolve_workspace_path(ctx.workspace_root, relative_path)
        if target.exists():
            # Notes accumulate over a run; never silently clobber an earlier one.
            stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{filename[:-3]}-{stamp}.md"
            relative_path = f"{NOTES_DIR}/{filename}"
            target = resolve_workspace_path(ctx.workspace_root, relative_path)

        target.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# {args.title}", ""]
        if args.source_url:
            lines.append(f"Source: {args.source_url}")
            lines.append("")
        lines.append(args.content)
        body = "\n".join(lines) + "\n"

        tmp_path = target.with_name(target.name + ".tmp")
        try:
            tmp_path.write_text(body, encoding="utf-8")
            tmp_path.replace(target)
        except OSError as exc:
            raise ToolError(f"Could not write research note: {exc}") from exc

        return StoreResearchNoteOutput(path=relative_path, bytes_written=len(body.encode("utf-8")))


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "note"
