from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables or a .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./reports.db"

    # "fake" returns a deterministic report without any network call (dev and tests).
    # "openai" calls any OpenAI-compatible /chat/completions endpoint.
    llm_provider: Literal["fake", "openai"] = "fake"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30.0

    # How many recent messages are sent to the model as context.
    max_messages_in_context: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
