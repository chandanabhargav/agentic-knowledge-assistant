# backend/core/settings.py
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Models / Keys
    OPENAI_API_KEY: str = Field(default="")
    EMBED_MODEL: str = Field(default="text-embedding-3-small")
    ANSWER_MODEL: str = Field(default="gpt-4o-mini")

    # Auth
    BEARER_TOKEN: str = Field(default="dev-token-please-change")

    # Paths
    DATA_DIR: str = Field(default="./data")
    INDEX_DIR: str = Field(default="./index_store/chroma_db")

    # CORS
    CORS_ALLOW_ORIGINS: List[str] = ["*"]

    # pydantic-settings config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown envs
    )

settings = Settings()
