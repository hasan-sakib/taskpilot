from pydantic import BaseModel, Field

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.agent.tools.web_research.search_provider import (
    DuckDuckGoHTMLProvider,
    SearchProviderError,
)

MAX_RESULTS_CAP = 20


class WebSearchInput(BaseModel):
    query: str
    max_results: int = Field(default=5, ge=1, le=MAX_RESULTS_CAP)


class WebSearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str


class WebSearchOutput(BaseModel):
    query: str
    results: list[WebSearchResultItem]


class WebSearchTool(Tool):
    name = "web_research.search"
    category = ToolCategory.WEB_RESEARCH
    description = "Search the public web and return titles, URLs, and snippets."
    input_schema = WebSearchInput
    output_schema = WebSearchOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 15

    def __init__(self, provider=None) -> None:
        self._provider = provider or DuckDuckGoHTMLProvider()

    async def run(self, args: WebSearchInput, ctx: ToolRunContext) -> WebSearchOutput:
        try:
            results = await self._provider.search(args.query, args.max_results)
        except SearchProviderError as exc:
            # Clearly report the limitation rather than silently returning nothing --
            # the agent (and any human watching) needs to know search wasn't available.
            raise ToolError(f"Web search is currently unavailable: {exc}") from exc

        return WebSearchOutput(
            query=args.query,
            results=[
                WebSearchResultItem(title=r.title, url=r.url, snippet=r.snippet) for r in results
            ],
        )
