import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    # Environment-only configuration keeps secrets out of source and images.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./processpilot.db")
    app_env: str = os.getenv("APP_ENV", "development")
    orchestrate_shared_secret: str | None = os.getenv("ORCHESTRATE_SHARED_SECRET")
    watson_discovery_url: str | None = os.getenv("WATSON_DISCOVERY_URL")
    watson_discovery_apikey: str | None = os.getenv("WATSON_DISCOVERY_APIKEY")
    watson_discovery_project_id: str | None = os.getenv("WATSON_DISCOVERY_PROJECT_ID")


@lru_cache
def get_settings() -> Settings:
    return Settings()
