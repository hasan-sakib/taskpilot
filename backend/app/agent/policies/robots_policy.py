from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.agent.tools.web_research.search_provider import USER_AGENT


async def is_fetch_allowed(url: str) -> bool:
    """Check robots.txt for `url`.

    Fails open (allows the fetch) when robots.txt can't be reached at all (network
    error/timeout -- keeps one flaky site from breaking research entirely) or when the
    site is reachable but has no robots.txt (a 404 there is the standard way a site
    says "no restrictions", per RFC 9309 and common crawler behavior). Fails CLOSED
    (disallows the fetch) when the server responds but errors on robots.txt itself
    (5xx): the site IS up, and RFC 9309 section 2.3.1.3 specifically calls out treating
    a server error on robots.txt as "fully disallowed" as reasonable crawler behavior,
    rather than assuming unrestricted access just because the policy file happened to
    500 -- unlike a total network failure, this isn't "can't tell", it's "site is
    actively erroring on the thing that would tell us."
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return True

    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(robots_url)
    except httpx.HTTPError:
        return True

    if response.status_code >= 500:
        return False
    if response.status_code >= 400:
        return True

    parser = RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)
