"""Keeps live Playwright browser/page objects alive across separate tool calls.

Each browser.* tool invocation is an independent function call with no shared memory
other than the DB -- but a Playwright Page is a live, stateful object that cannot be
persisted there. This process-global registry is what lets browser.navigate (one call)
and a later browser.click (a separate call) operate on the same actual browser tab.
Acceptable for a single-process, single-user, local-first app; if the backend process
restarts, all live sessions are lost -- known limitation, not reconciled automatically.
"""

from dataclasses import dataclass

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


class BrowserSessionNotFoundError(Exception):
    pass


@dataclass
class _LiveSession:
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page


class BrowserSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, _LiveSession] = {}

    async def start(self, session_id: str, *, headless: bool) -> Page:
        playwright = await async_playwright().start()
        try:
            browser = await playwright.chromium.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()
        except Exception:
            await playwright.stop()
            raise
        self._sessions[session_id] = _LiveSession(playwright, browser, context, page)
        return page

    def get_page(self, session_id: str) -> Page:
        live = self._sessions.get(session_id)
        if live is None:
            raise BrowserSessionNotFoundError(
                f"No active browser session: {session_id} "
                "(it may not have been started, or was already closed)"
            )
        return live.page

    def is_active(self, session_id: str) -> bool:
        return session_id in self._sessions

    async def close(self, session_id: str) -> None:
        live = self._sessions.pop(session_id, None)
        if live is None:
            return
        await live.context.close()
        await live.browser.close()
        await live.playwright.stop()


_manager = BrowserSessionManager()


def get_session_manager() -> BrowserSessionManager:
    return _manager
