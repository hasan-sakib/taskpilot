from pydantic import BaseModel

from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.browser.session_manager import get_session_manager
from app.db.base import new_uuid, utcnow
from app.db.models.browser_session import BrowserSession
from app.db.models.enums import BrowserSessionStatus


class StartSessionInput(BaseModel):
    headless: bool | None = None


class StartSessionOutput(BaseModel):
    session_id: str


class StartSessionTool(Tool):
    name = "browser.start_session"
    category = ToolCategory.BROWSER
    description = "Start a new browser session for navigating and interacting with web pages."
    input_schema = StartSessionInput
    output_schema = StartSessionOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 30

    async def run(self, args: StartSessionInput, ctx: ToolRunContext) -> StartSessionOutput:
        headless = args.headless if args.headless is not None else ctx.settings.browser_headless
        session_id = new_uuid()
        manager = get_session_manager()

        try:
            await manager.start(session_id, headless=headless)
        except Exception as exc:
            raise ToolError(f"Could not start browser session: {exc}") from exc

        async with ctx.session_factory() as session:
            session.add(
                BrowserSession(
                    id=session_id,
                    run_id=ctx.run_id,
                    task_id=ctx.task_id,
                    status=BrowserSessionStatus.ACTIVE,
                    headless=headless,
                    started_at=utcnow(),
                )
            )
            await session.commit()

        return StartSessionOutput(session_id=session_id)
