"""URL / path guards for Visual Engine (Forge-aware localhost)."""

from __future__ import annotations

from typing import Optional, Set
from urllib.parse import urlparse

ALLOWED_PROTOCOLS = {"http:", "https:"}


def is_loopback_host(hostname: str) -> bool:
    h = (hostname or "").lower().strip("[]")
    return h in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def validate_compare_url(
    url: str,
    *,
    allowed_loopback_ports: Optional[Set[int]] = None,
    allow_external: bool = True,
) -> None:
    """Raise ValueError if URL is not allowed.

    Unlike puppeteer-compare (which blocked all localhost), Forge *must* allow
    loopback ports belonging to the project's preview session.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL is required")
    if len(url) > 2048:
        raise ValueError("URL exceeds maximum length")
    try:
        parsed = urlparse(url)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid URL: {exc}") from exc
    scheme = f"{parsed.scheme}:"
    if scheme not in ALLOWED_PROTOCOLS:
        raise ValueError("Only http and https are allowed")
    host = parsed.hostname or ""
    if is_loopback_host(host):
        ports = allowed_loopback_ports or set()
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        # Preview static via Forge itself uses the platform port; allow common forge + preview band.
        if port not in ports and port not in range(9200, 9300) and port not in {8787, 80, 443}:
            raise ValueError(
                f"Loopback port {port} is not an allowed Forge preview port"
            )
        return
    # Block obvious cloud metadata / link-local
    if host.startswith("169.254.") or host == "metadata.google.internal":
        raise ValueError("Blocked host")
    if not allow_external:
        raise ValueError("External URLs are disabled")
