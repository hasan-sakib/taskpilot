from pydantic import BaseModel

from app.agent.policies.domain_policy import is_domain_allowed
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.browser.session_manager import BrowserSessionNotFoundError, get_session_manager
from app.db.models.browser_session import BrowserSession


class NavigateInput(BaseModel):
    session_id: str
    url: str


class NavigateOutput(BaseModel):
    url: str
    title: str


class NavigateTool(Tool):
    name = "browser.navigate"
    category = ToolCategory.BROWSER
    description = "Navigate the browser session to a URL."
    input_schema = NavigateInput
    output_schema = NavigateOutput
    # Plain navigation (following a link, loading a page) is not itself a consequential
    # action in the send-message/submit-form sense the security model targets -- that
    # gate lives on browser.click, which is what actually triggers a submission. This
    # stays usable for a research agent that needs to visit many pages. The allowed-
    # domains list (when configured) is still enforced as a hard block below, not an
    # approval prompt.
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 30

    async def run(self, args: NavigateInput, ctx: ToolRunContext) -> NavigateOutput:
        if not is_domain_allowed(args.url, ctx.settings.browser_allowed_domains):
            raise ToolError(f"Domain not in the configured allowlist: {args.url}")

        manager = get_session_manager()
        try:
            page = manager.get_page(args.session_id)
        except BrowserSessionNotFoundError as exc:
            raise ToolError(str(exc)) from exc

        try:
            await page.goto(args.url, wait_until="domcontentloaded")
        except Exception as exc:
            raise ToolError(f"Navigation failed: {exc}") from exc

        title = await page.title()

        async with ctx.session_factory() as session:
            browser_session = await session.get(BrowserSession, args.session_id)
            if browser_session is not None:
                browser_session.current_url = page.url
                await session.commit()

        return NavigateOutput(url=page.url, title=title)
