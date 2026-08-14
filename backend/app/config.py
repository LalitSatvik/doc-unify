"""Runtime configuration, sourced from environment variables (see
`.env.example` at the repo root). Every setting has a default that works
with the docker-compose stack out of the box.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres (+pgvector) connection.
    database_url: str = (
        "postgresql+psycopg://docunify:docunify@localhost:5432/docunify"
    )

    # Which LLMProvider implementation backs the app. "ollama" is the
    # default, fully-local path; "cloud" backs the hosted demo.
    llm_provider: str = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen2.5:7b"
    ollama_embed_model: str = "nomic-embed-text"

    # Fixed at the pgvector column width for the `chunks` table (migration
    # 0002). Changing the embed model to one with a different output
    # dimension requires a new migration to alter this column.
    embedding_dim: int = 768

    # Populated only when llm_provider == "cloud".
    cloud_api_key: str | None = None
    cloud_base_url: str | None = None
    cloud_chat_model: str | None = None

    cors_allow_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
