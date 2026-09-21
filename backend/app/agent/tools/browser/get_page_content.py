from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.browser.session_manager import BrowserSessionNotFoundError, get_session_manager

MAX_CONTENT_CHARS = 20_000


class GetPageContentInput(BaseModel):
    session_id: str


class GetPageContentOutput(BaseModel):
    url: str
    title: str
    text: str
    truncated: bool


class GetPageContentTool(Tool):
    name = "browser.get_page_content"
    category = ToolCategory.BROWSER
    description = "Read the current page's URL, title, and visible text content."
    input_schema = GetPageContentInput
    output_schema = GetPageContentOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 15

    async def run(self, args: GetPageContentInput, ctx: ToolRunContext) -> GetPageContentOutput:
        manager = get_session_manager()
        try:
            page = manager.get_page(args.session_id)
        except BrowserSessionNotFoundError as exc:
            raise ToolError(str(exc)) from exc

        try:
            title = await page.title()
            text = await page.inner_text("body")
        except Exception as exc:
            raise ToolError(f"Could not read page content: {exc}") from exc

        text = " ".join(text.split())
        return GetPageContentOutput(
            url=page.url,
            title=title,
            text=text[:MAX_CONTENT_CHARS],
            truncated=len(text) > MAX_CONTENT_CHARS,
        )
