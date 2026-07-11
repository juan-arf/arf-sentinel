"""
Authentication helper for CRAFT MCP.

Provides a function to obtain an authenticated HTTPX client configured
with the Bearer token and the X‑Project‑ID header required by the CRAFT
server.  In the hackathon prototype, the token defaults to "demo-token"
so that the app can run without a real identity provider.
"""

import os, httpx
from .config import settings


async def authenticate() -> httpx.AsyncClient:
    """
    Create an authenticated async HTTPX client for CRAFT MCP.

    Reads the bearer token from the environment variable `CRAFT_TOKEN`
    (falls back to "demo-token" if not set) and attaches it along with
    the project ID to every request.

    Returns
    -------
    httpx.AsyncClient
        A client with the base URL set to `settings.MCP_URL` and the
        required headers pre‑configured.
    """
    token = os.getenv("CRAFT_TOKEN", "demo-token")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Project-ID": settings.PROJECT_ID,
    }
    return httpx.AsyncClient(headers=headers, base_url=settings.MCP_URL)
