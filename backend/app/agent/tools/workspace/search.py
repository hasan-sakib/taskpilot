from pydantic import BaseModel, Field

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext

MAX_RESULTS_CAP = 100
MAX_CONTENT_SCAN_BYTES = 500_000  # skip content search inside very large files
SNIPPET_RADIUS = 60


class SearchInput(BaseModel):
    query: str
    path: str = Field(default=".", description="Directory to search under, relative to workspace")
    search_content: bool = True
    max_results: int = Field(default=20, ge=1, le=MAX_RESULTS_CAP)


class SearchMatch(BaseModel):
    path: str
    match_type: str  # "name" | "content"
    snippet: str | None = None


class SearchOutput(BaseModel):
    query: str
    matches: list[SearchMatch]
    truncated: bool


class SearchTool(Tool):
    name = "workspace.search"
    category = ToolCategory.WORKSPACE
    description = "Search file names, and optionally file content, under a workspace directory."
    input_schema = SearchInput
    output_schema = SearchOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 20

    async def run(self, args: SearchInput, ctx: ToolRunContext) -> SearchOutput:
        root = resolve_workspace_path(ctx.workspace_root, args.path)
        if not root.exists() or not root.is_dir():
            raise ToolError(f"Not a directory: {args.path}")

        needle = args.query.lower()
        matches: list[SearchMatch] = []
        workspace_root = ctx.workspace_root.resolve()

        for file_path in sorted(root.rglob("*")):
            if len(matches) >= args.max_results:
                break
            if not file_path.is_file():
                continue
            relative = str(file_path.relative_to(workspace_root))

            if needle in file_path.name.lower():
                matches.append(SearchMatch(path=relative, match_type="name"))
                continue

            if args.search_content and file_path.stat().st_size <= MAX_CONTENT_SCAN_BYTES:
                snippet = _find_content_snippet(file_path, needle)
                if snippet is not None:
                    matches.append(
                        SearchMatch(path=relative, match_type="content", snippet=snippet)
                    )

        return SearchOutput(
            query=args.query,
            matches=matches[: args.max_results],
            truncated=len(matches) >= args.max_results,
        )


def _find_content_snippet(file_path, needle: str) -> str | None:
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    idx = text.lower().find(needle)
    if idx == -1:
        return None
    start = max(0, idx - SNIPPET_RADIUS)
    end = min(len(text), idx + len(needle) + SNIPPET_RADIUS)
    return text[start:end].replace("\n", " ").strip()
