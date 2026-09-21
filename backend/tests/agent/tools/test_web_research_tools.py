import httpx
import pytest

from app.agent.tools.base import ToolError
from app.agent.tools.web_research.open_url import OpenUrlInput, OpenUrlTool
from app.agent.tools.web_research.search import WebSearchInput, WebSearchTool
from app.agent.tools.web_research.search_provider import (
    SearchProvider,
    SearchProviderError,
    SearchResult,
)
from app.agent.tools.web_research.store_research_note import (
    StoreResearchNoteInput,
    StoreResearchNoteTool,
)
from app.agent.tools.web_research.summarize import SummarizeInput, SummarizeTool


class _FakeSearchProvider(SearchProvider):
    def __init__(self, results=None, error=None):
        self._results = results or []
        self._error = error

    async def search(self, query, max_results):
        if self._error:
            raise self._error
        return self._results[:max_results]


# --- search ---


@pytest.mark.asyncio
async def test_web_search_returns_results(run_ctx):
    provider = _FakeSearchProvider(
        results=[SearchResult(title="Example", url="https://example.com", snippet="hi")]
    )
    out = await WebSearchTool(provider=provider).run(WebSearchInput(query="example"), run_ctx)
    assert len(out.results) == 1
    assert out.results[0].url == "https://example.com"


@pytest.mark.asyncio
async def test_web_search_reports_provider_failure_as_tool_error(run_ctx):
    provider = _FakeSearchProvider(error=SearchProviderError("network down"))
    with pytest.raises(ToolError):
        await WebSearchTool(provider=provider).run(WebSearchInput(query="x"), run_ctx)


def test_web_search_is_auto_approved():
    decision = WebSearchTool().evaluate_permission({}, {})
    assert decision.requires_approval is False


# --- open_url ---


def _mock_client_for(html: str, status_code: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=html)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_open_url_extracts_title_and_text(run_ctx, monkeypatch):
    html = "<html><head><title>My Page</title></head><body><script>bad()</script>"
    html += "<p>Hello   world.</p></body></html>"

    async def fake_is_fetch_allowed(url):
        return True

    monkeypatch.setattr(
        "app.agent.tools.web_research.open_url.is_fetch_allowed", fake_is_fetch_allowed
    )

    import httpx as httpx_module

    real_async_client = httpx_module.AsyncClient

    def fake_async_client(*args, **kwargs):
        kwargs["transport"] = _mock_client_for(html)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(
        "app.agent.tools.web_research.open_url.httpx.AsyncClient", fake_async_client
    )

    out = await OpenUrlTool().run(OpenUrlInput(url="https://example.com"), run_ctx)
    assert out.title == "My Page"
    assert "Hello world." in out.content
    assert "bad()" not in out.content


@pytest.mark.asyncio
async def test_open_url_rejects_disallowed_scheme(run_ctx):
    with pytest.raises(ToolError):
        await OpenUrlTool().run(OpenUrlInput(url="ftp://example.com/file"), run_ctx)


@pytest.mark.asyncio
async def test_open_url_respects_robots_disallow(run_ctx, monkeypatch):
    async def fake_is_fetch_allowed(url):
        return False

    monkeypatch.setattr(
        "app.agent.tools.web_research.open_url.is_fetch_allowed", fake_is_fetch_allowed
    )
    with pytest.raises(ToolError):
        await OpenUrlTool().run(OpenUrlInput(url="https://example.com/private"), run_ctx)


# --- summarize ---


@pytest.mark.asyncio
async def test_summarize_calls_llm_provider(run_ctx):
    out = await SummarizeTool().run(SummarizeInput(text="a long article " * 10), run_ctx)
    assert out.summary == "Test completion."
    assert run_ctx.llm_provider.completion_prompts  # prompt was actually sent


# --- store_research_note ---


@pytest.mark.asyncio
async def test_store_research_note_writes_markdown(workspace_root, run_ctx):
    out = await StoreResearchNoteTool().run(
        StoreResearchNoteInput(
            title="Company X salary data", content="Found range $100-120k.",
            source_url="https://example.com/salaries",
        ),
        run_ctx,
    )
    assert out.path == "research/company-x-salary-data.md"
    written = (workspace_root / out.path).read_text()
    assert "Company X salary data" in written
    assert "https://example.com/salaries" in written
    assert "Found range $100-120k." in written


@pytest.mark.asyncio
async def test_store_research_note_never_clobbers_existing_note(workspace_root, run_ctx):
    tool = StoreResearchNoteTool()
    first = await tool.run(StoreResearchNoteInput(title="Note", content="v1"), run_ctx)
    second = await tool.run(StoreResearchNoteInput(title="Note", content="v2"), run_ctx)
    assert first.path != second.path
    assert (workspace_root / first.path).read_text().count("v1") == 1
    assert "v2" in (workspace_root / second.path).read_text()


def test_store_research_note_is_auto_approved():
    decision = StoreResearchNoteTool().evaluate_permission({}, {})
    assert decision.requires_approval is False
