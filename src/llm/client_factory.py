"""Factory for creating LLM clients based on environment configuration.

This module handles the logic of selecting and instantiating the
appropriate LLM client implementation based on environment variables.
"""
from __future__ import annotations

import os

from src.config import (
    LLM_API_KEY_ENV,
    LLM_MODEL_DEFAULT,
    LLM_BASE_URL,
    get_llm_api_key,
    get_llm_model,
)
from src.llm.providers.base import BaseLLMClient
from src.llm.providers.openai_compat import OpenAICompatibleClient


def create_llm_client(
    api_key: str | None = None,
    model: str | None = None,
) -> BaseLLMClient:
    """Create an LLM client based on environment configuration.

    Args:
        api_key: Override API key (uses environment if not provided)
        model: Override model name (uses environment if not provided)

    Returns:
        An initialized LLM client instance

    Raises:
        RuntimeError: If required configuration is missing
    """
    provider = os.getenv("LLM_PROVIDER", "openai-compat").strip().lower()

    if api_key is None:
        api_key = get_llm_api_key()
    if model is None:
        model = get_llm_model()

    if provider == "openai-compat":
        base_url = os.getenv("LLM_BASE_URL", LLM_BASE_URL).strip()
        return OpenAICompatibleClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            "Supported providers: openai-compat. "
            "Set LLM_PROVIDER environment variable to select."
        )
