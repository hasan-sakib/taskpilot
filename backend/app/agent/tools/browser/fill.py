from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.browser.session_manager import BrowserSessionNotFoundError, get_session_manager


class FillInput(BaseModel):
    session_id: str
    selector: str
    value: str


class FillOutput(BaseModel):
    selector: str
    filled: bool


class FillTool(Tool):
    name = "browser.fill"
    category = ToolCategory.BROWSER
    description = "Fill a visible input field on the current page. Does not submit anything."
    input_schema = FillInput
    output_schema = FillOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 15

    async def run(self, args: FillInput, ctx: ToolRunContext) -> FillOutput:
        manager = get_session_manager()
        try:
            page = manager.get_page(args.session_id)
        except BrowserSessionNotFoundError as exc:
            raise ToolError(str(exc)) from exc

        try:
            await page.fill(args.selector, args.value, timeout=10_000)
        except Exception as exc:
            raise ToolError(f"Could not fill '{args.selector}': {exc}") from exc

        return FillOutput(selector=args.selector, filled=True)
