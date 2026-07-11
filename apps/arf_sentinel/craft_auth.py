import os, httpx
from .config import settings

async def authenticate() -> httpx.AsyncClient:
    token = os.getenv("CRAFT_TOKEN", "demo-token")
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Project-ID": settings.PROJECT_ID
    }
    return httpx.AsyncClient(headers=headers, base_url=settings.MCP_URL)
