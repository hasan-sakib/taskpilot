import httpx
import pytest

from app.agent.policies.robots_policy import is_fetch_allowed


def _mock_transport(status_code: int, body: str = "") -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=body)

    return httpx.MockTransport(handler)


def _patch_client(monkeypatch, transport: httpx.MockTransport) -> None:
    real_async_client = httpx.AsyncClient

    def fake_async_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("app.agent.policies.robots_policy.httpx.AsyncClient", fake_async_client)


@pytest.mark.asyncio
async def test_allows_when_robots_txt_missing(monkeypatch):
    _patch_client(monkeypatch, _mock_transport(404))
    assert await is_fetch_allowed("https://example.com/page") is True


@pytest.mark.asyncio
async def test_disallows_when_robots_txt_server_errors(monkeypatch):
    # A 5xx means the site IS up but is actively erroring on the thing that would tell
    # us its policy -- fail closed, not open (this was a real, fixed bug: the code
    # previously fail-opened on the entire 400-599 range).
    _patch_client(monkeypatch, _mock_transport(503))
    assert await is_fetch_allowed("https://example.com/page") is False


@pytest.mark.asyncio
async def test_allows_when_robots_txt_is_unreachable(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    _patch_client(monkeypatch, httpx.MockTransport(handler))
    assert await is_fetch_allowed("https://example.com/page") is True


@pytest.mark.asyncio
async def test_respects_explicit_disallow(monkeypatch):
    _patch_client(
        monkeypatch, _mock_transport(200, "User-agent: *\nDisallow: /private\n")
    )
    assert await is_fetch_allowed("https://example.com/private/page") is False
    assert await is_fetch_allowed("https://example.com/public/page") is True


@pytest.mark.asyncio
async def test_non_http_url_is_allowed_without_a_request():
    assert await is_fetch_allowed("not-a-url") is True
