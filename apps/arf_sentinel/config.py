import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

class Settings:
    MCP_URL: str = os.getenv("MCP_URL", "")
    PROJECT_ID: str = os.getenv("PROJECT_ID", "")
    NEBIUS_API_KEY: str = os.getenv("NEBIUS_API_KEY", "")
    NEBIUS_BASE_URL: str = os.getenv("NEBIUS_BASE_URL", "https://api.nebius.com/v1")
    NEBIUS_MODEL: str = os.getenv("NEBIUS_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    DEMO_MODE: bool = os.getenv("SENTINEL_DEMO_MODE", "false").lower() == "true"

settings = Settings()
