from datetime import datetime

from pydantic import BaseModel

from app.agent.policies.workspace_policy import resolve_workspace_path
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.browser.session_manager import BrowserSessionNotFoundError, get_session_manager

SCREENSHOTS_DIR = "exports/screenshots"


class ScreenshotInput(BaseModel):
    session_id: str


class ScreenshotOutput(BaseModel):
    path: str


class ScreenshotTool(Tool):
    name = "browser.screenshot"
    category = ToolCategory.BROWSER
    description = "Capture a screenshot of the current page and save it to the workspace."
    input_schema = ScreenshotInput
    output_schema = ScreenshotOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 15

    async def run(self, args: ScreenshotInput, ctx: ToolRunContext) -> ScreenshotOutput:
        manager = get_session_manager()
        try:
            page = manager.get_page(args.session_id)
        except BrowserSessionNotFoundError as exc:
            raise ToolError(str(exc)) from exc

        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        relative_path = f"{SCREENSHOTS_DIR}/{args.session_id}-{stamp}.png"
        target = resolve_workspace_path(ctx.workspace_root, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        try:
            await page.screenshot(path=str(target))
        except Exception as exc:
            raise ToolError(f"Could not capture screenshot: {exc}") from exc

        return ScreenshotOutput(path=relative_path)
