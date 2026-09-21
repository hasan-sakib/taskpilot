from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.browser.session_manager import BrowserSessionNotFoundError, get_session_manager


class SelectOptionInput(BaseModel):
    session_id: str
    selector: str
    value: str


class SelectOptionOutput(BaseModel):
    selector: str
    selected_value: str


class SelectOptionTool(Tool):
    name = "browser.select_option"
    category = ToolCategory.BROWSER
    description = "Select an option in a visible <select> dropdown on the current page."
    input_schema = SelectOptionInput
    output_schema = SelectOptionOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 15

    async def run(self, args: SelectOptionInput, ctx: ToolRunContext) -> SelectOptionOutput:
        manager = get_session_manager()
        try:
            page = manager.get_page(args.session_id)
        except BrowserSessionNotFoundError as exc:
            raise ToolError(str(exc)) from exc

        try:
            await page.select_option(args.selector, args.value, timeout=10_000)
        except Exception as exc:
            raise ToolError(f"Could not select option on '{args.selector}': {exc}") from exc

        return SelectOptionOutput(selector=args.selector, selected_value=args.value)
