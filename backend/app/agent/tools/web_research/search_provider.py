from abc import ABC, abstractmethod
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

USER_AGENT = "TaskPilot/0.1 (local personal agent; +https://github.com/)"


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class SearchProviderError(Exception):
    """Raised when a search request fails or returns nothing parseable."""


class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, max_results: int) -> list[SearchResult]: ...


class DuckDuckGoHTMLProvider(SearchProvider):
    """No-API-key search via DuckDuckGo's static HTML results endpoint.

    This is inherently fragile (screen-scraping a page DuckDuckGo doesn't guarantee
    the structure of, subject to markup drift, rate limiting, or ToS changes) --
    documented as a known limitation. The SearchProvider interface is what makes
    swapping in an API-key-based provider later a config change, not a rewrite.
    """

    _URL = "https://html.duckduckgo.com/html/"

    async def search(self, query: str, max_results: int) -> list[SearchResult]:
        try:
            async with httpx.AsyncClient(
                timeout=10.0, headers={"User-Agent": USER_AGENT}
            ) as client:
                response = await client.get(self._URL, params={"q": query})
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SearchProviderError(f"Search request failed: {exc}") from exc

        soup = BeautifulSoup(response.text, "html.parser")
        results: list[SearchResult] = []
        for node in soup.select(".result"):
            link = node.select_one(".result__a")
            if link is None or not link.get("href"):
                continue
            snippet_node = node.select_one(".result__snippet")
            results.append(
                SearchResult(
                    title=link.get_text(strip=True),
                    url=_unwrap_redirect(link["href"]),
                    snippet=snippet_node.get_text(strip=True) if snippet_node else "",
                )
            )
            if len(results) >= max_results:
                break

        return results


def _unwrap_redirect(href: str) -> str:
    """DuckDuckGo's HTML endpoint sometimes wraps result links in a `/l/?uddg=` redirect."""
    parsed = urlparse(href)
    if parsed.path == "/l/":
        target = parse_qs(parsed.query).get("uddg")
        if target:
            return target[0]
    if href.startswith("//"):
        return f"https:{href}"
    return href
