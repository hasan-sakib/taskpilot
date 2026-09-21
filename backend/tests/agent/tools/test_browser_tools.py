from urllib.parse import quote

import pytest

from app.agent.tools.base import PermissionLevel, ToolError
from app.agent.tools.browser.click import ClickInput, ClickTool
from app.agent.tools.browser.close_session import CloseSessionInput, CloseSessionTool
from app.agent.tools.browser.fill import FillInput, FillTool
from app.agent.tools.browser.get_page_content import GetPageContentInput, GetPageContentTool
from app.agent.tools.browser.navigate import NavigateInput, NavigateTool
from app.agent.tools.browser.screenshot import ScreenshotInput, ScreenshotTool
from app.agent.tools.browser.select_option import SelectOptionInput, SelectOptionTool
from app.agent.tools.browser.start_session import StartSessionInput, StartSessionTool
from app.browser.session_manager import get_session_manager
from app.db.models.agent_run import AgentRun
from app.db.models.agent_task import AgentTask
from app.db.models.browser_session import BrowserSession
from app.db.models.enums import BrowserSessionStatus, RunStatus, TaskStatus

TEST_PAGE_HTML = """
<html>
<head><title>Test Page</title></head>
<body>
  <p id="greeting">Hello, world.</p>
  <form>
    <input id="name" name="name" />
    <select id="color"><option value="red">Red</option><option value="blue">Blue</option></select>
    <button id="submit-btn" type="button"
      onclick="document.getElementById('result').innerText='clicked'">
      Submit
    </button>
  </form>
  <p id="result"></p>
</body>
</html>
"""
TEST_PAGE_URL = "data:text/html," + quote(TEST_PAGE_HTML)


@pytest.fixture(autouse=True)
async def _seed_run_and_task(agent_session_factory, run_ctx):
    async with agent_session_factory() as session:
        session.add(
            AgentRun(
                id=run_ctx.run_id, goal="g", status=RunStatus.RUNNING, workspace_root="/w"
            )
        )
        session.add(
            AgentTask(
                id=run_ctx.task_id,
                run_id=run_ctx.run_id,
                plan_version=1,
                sequence_index=0,
                description="d",
                tool_name="browser.start_session",
                tool_args={},
                status=TaskStatus.IN_PROGRESS,
            )
        )
        await session.commit()


@pytest.fixture
async def session_id(run_ctx):
    out = await StartSessionTool().run(StartSessionInput(headless=True), run_ctx)
    yield out.session_id
    await get_session_manager().close(out.session_id)


@pytest.mark.asyncio
async def test_start_session_creates_db_row_and_live_session(agent_session_factory, run_ctx):
    out = await StartSessionTool().run(StartSessionInput(headless=True), run_ctx)
    try:
        assert get_session_manager().is_active(out.session_id)
        async with agent_session_factory() as session:
            row = await session.get(BrowserSession, out.session_id)
            assert row.status == BrowserSessionStatus.ACTIVE
            assert row.run_id == run_ctx.run_id
    finally:
        await get_session_manager().close(out.session_id)


@pytest.mark.asyncio
async def test_navigate_loads_page_and_updates_db(agent_session_factory, run_ctx, session_id):
    out = await NavigateTool().run(NavigateInput(session_id=session_id, url=TEST_PAGE_URL), run_ctx)
    assert out.title == "Test Page"

    async with agent_session_factory() as session:
        row = await session.get(BrowserSession, session_id)
        assert row.current_url == out.url


@pytest.mark.asyncio
async def test_navigate_rejects_disallowed_domain(run_ctx, session_id):
    run_ctx.settings.browser_allowed_domains_raw = "example.com"
    try:
        with pytest.raises(ToolError):
            await NavigateTool().run(
                NavigateInput(session_id=session_id, url="https://not-allowed.test/"), run_ctx
            )
    finally:
        run_ctx.settings.browser_allowed_domains_raw = ""


@pytest.mark.asyncio
async def test_navigate_unknown_session_raises_tool_error(run_ctx):
    with pytest.raises(ToolError):
        await NavigateTool().run(NavigateInput(session_id="missing", url=TEST_PAGE_URL), run_ctx)


@pytest.mark.asyncio
async def test_get_page_content_returns_visible_text(run_ctx, session_id):
    await NavigateTool().run(NavigateInput(session_id=session_id, url=TEST_PAGE_URL), run_ctx)
    out = await GetPageContentTool().run(GetPageContentInput(session_id=session_id), run_ctx)
    assert "Hello, world." in out.text
    assert out.title == "Test Page"


@pytest.mark.asyncio
async def test_fill_sets_input_value(run_ctx, session_id):
    await NavigateTool().run(NavigateInput(session_id=session_id, url=TEST_PAGE_URL), run_ctx)
    out = await FillTool().run(
        FillInput(session_id=session_id, selector="#name", value="Ada"), run_ctx
    )
    assert out.filled is True

    page = get_session_manager().get_page(session_id)
    assert await page.input_value("#name") == "Ada"


@pytest.mark.asyncio
async def test_select_option_sets_dropdown_value(run_ctx, session_id):
    await NavigateTool().run(NavigateInput(session_id=session_id, url=TEST_PAGE_URL), run_ctx)
    out = await SelectOptionTool().run(
        SelectOptionInput(session_id=session_id, selector="#color", value="blue"), run_ctx
    )
    assert out.selected_value == "blue"


@pytest.mark.asyncio
async def test_click_triggers_page_action(run_ctx, session_id):
    await NavigateTool().run(NavigateInput(session_id=session_id, url=TEST_PAGE_URL), run_ctx)
    await ClickTool().run(ClickInput(session_id=session_id, selector="#submit-btn"), run_ctx)

    page = get_session_manager().get_page(session_id)
    assert await page.inner_text("#result") == "clicked"


def test_click_requires_approval_by_default():
    assert ClickTool.default_permission == PermissionLevel.REQUIRES_APPROVAL
    assert ClickTool().evaluate_permission({}, {}).requires_approval is True


def test_navigate_is_auto_approved():
    assert NavigateTool().evaluate_permission({}, {}).requires_approval is False


@pytest.mark.asyncio
async def test_screenshot_writes_file_to_workspace(workspace_root, run_ctx, session_id):
    await NavigateTool().run(NavigateInput(session_id=session_id, url=TEST_PAGE_URL), run_ctx)
    out = await ScreenshotTool().run(ScreenshotInput(session_id=session_id), run_ctx)
    assert (workspace_root / out.path).exists()
    assert out.path.startswith("exports/screenshots/")


@pytest.mark.asyncio
async def test_close_session_ends_live_session_and_updates_db(agent_session_factory, run_ctx):
    started = await StartSessionTool().run(StartSessionInput(headless=True), run_ctx)
    out = await CloseSessionTool().run(
        CloseSessionInput(session_id=started.session_id), run_ctx
    )
    assert out.closed is True
    assert not get_session_manager().is_active(started.session_id)

    async with agent_session_factory() as session:
        row = await session.get(BrowserSession, started.session_id)
        assert row.status == BrowserSessionStatus.CLOSED
        assert row.closed_at is not None
