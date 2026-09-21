from urllib.parse import urlparse


def is_domain_allowed(url: str, allowed_domains: list[str]) -> bool:
    """Empty allowlist means unrestricted (no domains configured yet); a non-empty
    allowlist permits the exact domain or any subdomain of an allowed entry."""
    if not allowed_domains:
        return True

    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False

    for allowed in allowed_domains:
        allowed = allowed.lower().strip()
        if host == allowed or host.endswith(f".{allowed}"):
            return True
    return False
