"""Builds the `LLMProvider` the rest of the app uses, from `app.config.settings`.
The only place that reads `settings.llm_provider` — everything downstream
takes an `LLMProvider` and never asks which one it got."""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.llm.base import LLMProvider
from app.llm.ollama import OllamaProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "cloud":
        from app.llm.cloud import CloudProvider

        if not (
            settings.cloud_api_key
            and settings.cloud_base_url
            and settings.cloud_chat_model
            and settings.cloud_embed_model
        ):
            raise RuntimeError(
                "llm_provider=cloud requires cloud_api_key, cloud_base_url, "
                "cloud_chat_model, and cloud_embed_model to be set"
            )
        return CloudProvider(
            api_key=settings.cloud_api_key,
            base_url=settings.cloud_base_url,
            chat_model=settings.cloud_chat_model,
            embed_model=settings.cloud_embed_model,
            embedding_dim=settings.embedding_dim,
        )

    return OllamaProvider(
        chat_model=settings.ollama_chat_model,
        embed_model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
        embedding_dim=settings.embedding_dim,
    )
