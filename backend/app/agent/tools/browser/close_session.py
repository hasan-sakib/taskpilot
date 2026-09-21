from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolRunContext
from app.browser.session_manager import get_session_manager
from app.db.base import utcnow
from app.db.models.browser_session import BrowserSession
from app.db.models.enums import BrowserSessionStatus


class CloseSessionInput(BaseModel):
    session_id: str


class CloseSessionOutput(BaseModel):
    session_id: str
    closed: bool


class CloseSessionTool(Tool):
    name = "browser.close_session"
    category = ToolCategory.BROWSER
    description = "Close a browser session and free its resources."
    input_schema = CloseSessionInput
    output_schema = CloseSessionOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 15

    async def run(self, args: CloseSessionInput, ctx: ToolRunContext) -> CloseSessionOutput:
        manager = get_session_manager()
        was_active = manager.is_active(args.session_id)
        await manager.close(args.session_id)

        async with ctx.session_factory() as session:
            browser_session = await session.get(BrowserSession, args.session_id)
            if browser_session is not None:
                browser_session.status = BrowserSessionStatus.CLOSED
                browser_session.closed_at = utcnow()
                await session.commit()

        return CloseSessionOutput(session_id=args.session_id, closed=was_active)
