from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.browser.session_manager import BrowserSessionNotFoundError, get_session_manager


class ClickInput(BaseModel):
    session_id: str
    selector: str


class ClickOutput(BaseModel):
    url: str
    title: str


class ClickTool(Tool):
    name = "browser.click"
    category = ToolCategory.BROWSER
    description = "Click a visible element on the current page, identified by a CSS selector."
    input_schema = ClickInput
    output_schema = ClickOutput
    # The primary approval gate for browser automation: a click is what actually
    # triggers a form submission or "send" action, which the project's security model
    # requires a human to confirm before it happens. Navigation and reading are not
    # gated the same way (see browser.navigate).
    default_permission = PermissionLevel.REQUIRES_APPROVAL
    timeout_seconds = 15

    async def run(self, args: ClickInput, ctx: ToolRunContext) -> ClickOutput:
        manager = get_session_manager()
        try:
            page = manager.get_page(args.session_id)
        except BrowserSessionNotFoundError as exc:
            raise ToolError(str(exc)) from exc

        try:
            await page.click(args.selector, timeout=10_000)
        except Exception as exc:
            raise ToolError(f"Could not click '{args.selector}': {exc}") from exc

        return ClickOutput(url=page.url, title=await page.title())
