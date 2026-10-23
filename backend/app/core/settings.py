"""Application settings, read from environment variables and an optional .env file."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_NAME = "MeloMind"


class Settings(BaseSettings):
    """Every backend setting. Keys use SecretStr so they never show up in logs or reprs."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # App and database
    app_env: str = "development"
    frontend_origin: str = "http://localhost:5173"
    database_url: SecretStr = SecretStr("")

    # Supabase
    supabase_url: str = ""

    # Qloo
    qloo_api_key: SecretStr = SecretStr("")
    qloo_base_url: str = "https://hackathon.api.qloo.com"

    # YouTube
    youtube_api_key: SecretStr = SecretStr("")

    # LLM
    llm_provider: str = ""
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    llm_fallback_provider: str = ""
    llm_fallback_model: str = ""
    llm_fallback_api_key: SecretStr = SecretStr("")

    # Agent and limits
    agent_max_tool_calls: int = 12
    agent_max_model_calls: int = 8
    agent_timeout_seconds: int = 25
    resolve_max_searches: int = 5
    link_max_searches: int = 10
    agent_max_retries: int = 2
    session_target_minutes: int = 20
    plan_rate_limit_per_hour: int = 10

    # Person mode and Memory Graph
    warmup_pairs: int = 6
    memory_graph_max_nodes: int = 30


@lru_cache
def get_settings() -> Settings:
    """Return the settings, read once and cached for the life of the process."""
    return Settings()
