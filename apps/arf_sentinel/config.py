"""
Application configuration loaded from environment variables.

All settings are read from environment variables or a `.env` file
(using python-dotenv).  Sensible defaults are provided so that the
demo can run without a fully populated `.env` file in mock mode.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


class Settings:
    """
    Central configuration class.  Reads environment variables with
    sensible defaults.

    Attributes:
        MCP_URL: CRAFT MCP server URL.
        PROJECT_ID: CRAFT project identifier.
        NEBIUS_API_KEY: Nebius Token Factory API key.
        NEBIUS_BASE_URL: Nebius API base URL.
        NEBIUS_MODEL: Nemotron model name.
        DEMO_MODE: Whether to use pre‑captured fixture data.
    """
    MCP_URL: str = os.getenv("MCP_URL", "")
    PROJECT_ID: str = os.getenv("PROJECT_ID", "")
    NEBIUS_API_KEY: str = os.getenv("NEBIUS_API_KEY", "")
    NEBIUS_BASE_URL: str = os.getenv("NEBIUS_BASE_URL", "https://api.nebius.com/v1")
    NEBIUS_MODEL: str = os.getenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    DEMO_MODE: bool = os.getenv("SENTINEL_DEMO_MODE", "false").lower() == "true"


settings = Settings()
