import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

from app.agent.policies.robots_policy import is_fetch_allowed
from app.agent.tools.base import PermissionLevel, Tool, ToolCategory, ToolError, ToolRunContext
from app.agent.tools.web_research.search_provider import USER_AGENT

MAX_RESPONSE_BYTES = 5_000_000  # 5 MB
MAX_CONTENT_CHARS = 20_000
ALLOWED_SCHEMES = {"http", "https"}


class OpenUrlInput(BaseModel):
    url: str


class OpenUrlOutput(BaseModel):
    url: str
    title: str
    content: str
    truncated: bool


class OpenUrlTool(Tool):
    name = "web_research.open_url"
    category = ToolCategory.WEB_RESEARCH
    description = "Fetch a URL and extract its readable text content."
    input_schema = OpenUrlInput
    output_schema = OpenUrlOutput
    default_permission = PermissionLevel.AUTO
    timeout_seconds = 20

    async def run(self, args: OpenUrlInput, ctx: ToolRunContext) -> OpenUrlOutput:
        scheme = args.url.split("://", 1)[0].lower() if "://" in args.url else ""
        if scheme not in ALLOWED_SCHEMES:
            raise ToolError(f"Unsupported URL scheme: {args.url}")

        if not await is_fetch_allowed(args.url):
            raise ToolError(f"robots.txt disallows fetching this URL: {args.url}")

        try:
            async with httpx.AsyncClient(
                timeout=15.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True
            ) as client:
                async with client.stream("GET", args.url) as response:
                    response.raise_for_status()
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > MAX_RESPONSE_BYTES:
                            break
                    body = bytes(chunks)
        except httpx.HTTPError as exc:
            raise ToolError(f"Could not fetch URL: {exc}") from exc

        soup = BeautifulSoup(body, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "header", "footer"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else args.url
        text = " ".join(_main_content_node(soup).get_text(separator=" ").split())

        return OpenUrlOutput(
            url=args.url,
            title=title,
            content=text[:MAX_CONTENT_CHARS],
            truncated=len(text) > MAX_CONTENT_CHARS,
        )


def _main_content_node(soup: BeautifulSoup):
    """Prefer <main>/<article>/a #content-ish container over the whole page -- a naive
    whole-body text dump is dominated by nav/sidebar boilerplate on most real sites."""
    for selector in ("main", "article", "#content", "#main", ".content", ".main"):
        node = soup.select_one(selector)
        if node is not None and len(node.get_text(strip=True)) > 200:
            return node
    return soup.body or soup
