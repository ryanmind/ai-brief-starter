"""OpenAI-compatible API client implementation.

This implementation works with any OpenAI-compatible endpoint,
including: OpenAI official API, DashScope Qwen, Iflow, etc.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from openai import OpenAI

from src.config import (
    LLM_BASE_URL,
    LLM_CACHE_ENABLED,
    LLM_CACHE_PATH,
    LLM_CACHE_TTL,
    get_fallback_llm_models,
)
from src.llm.cache import LLMResponseCache
from src.llm.providers.base import BaseLLMClient

logger = logging.getLogger(__name__)

# Global cache instance (shared across all clients)
_cache_instance: LLMResponseCache | None = None


def _get_cache() -> LLMResponseCache | None:
    """Get or create the cache instance."""
    global _cache_instance
    if not LLM_CACHE_ENABLED:
        return None
    if _cache_instance is None:
        _cache_instance = LLMResponseCache(LLM_CACHE_PATH, LLM_CACHE_TTL)
    return _cache_instance


class OpenAICompatibleClient(BaseLLMClient):
    """LLM client for OpenAI-compatible APIs.

    Supports any endpoint that follows the OpenAI chat completion
    API convention, including:
    - Official OpenAI API
    - Alibaba Cloud DashScope (Qwen)
    - Iflow
    - Anthropic compatible proxies
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = LLM_BASE_URL,
    ):
        """Initialize the OpenAI-compatible client.

        Args:
            api_key: API key for authentication
            model: Model name to use
            base_url: Base URL for the API endpoint
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.fallback_models = get_fallback_llm_models()

    def get_provider_name(self) -> str:
        return "openai-compatible"

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        task_name: str = "unknown",
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
    ) -> str:
        # Check cache first for all models
        cache = _get_cache()
        models_to_try = [self.model] + self.fallback_models

        if cache is not None:
            for candidate_model in models_to_try:
                cached = cache.get(system_prompt, user_prompt, candidate_model)
                if cached is not None:
                    logger.debug(
                        "llm_call: cache_hit task=%s model=%s",
                        task_name,
                        candidate_model,
                    )
                    return cached

        # Estimate input tokens for logging
        input_chars = len(system_prompt) + len(user_prompt)
        estimated_input_tokens = (input_chars + 3) // 4

        last_error: Exception | None = None

        # Try each model in order: primary then fallbacks
        for model_idx, current_model in enumerate(models_to_try):
            is_fallback = model_idx > 0
            if is_fallback:
                logger.info(
                    "llm_call: trying fallback model task=%s primary=%s fallback=%d/%d",
                    task_name,
                    self.model,
                    model_idx,
                    len(self.fallback_models),
                )

            params = {
                "model": current_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "extra_body": {},
            }
            if max_tokens is not None and max_tokens > 0:
                params["max_tokens"] = max_tokens

            for attempt in range(max_retries):
                try:
                    start_time = time.time()
                    response = self.client.chat.completions.create(**params)
                    result = (response.choices[0].message.content or "").strip()
                    elapsed_ms = int((time.time() - start_time) * 1000)

                    # Get actual usage from response if available
                    actual_input_tokens = None
                    actual_output_tokens = None
                    if hasattr(response, 'usage') and response.usage is not None:
                        actual_input_tokens = getattr(response.usage, 'prompt_tokens', None)
                        actual_output_tokens = getattr(response.usage, 'completion_tokens', None)

                    # Estimate output tokens if not available
                    output_tokens = actual_output_tokens or ((len(result) + 3) // 4)
                    input_tokens = actual_input_tokens or estimated_input_tokens
                    total_tokens = input_tokens + output_tokens

                    # Cache the result
                    if cache is not None and result:
                        cache.set(system_prompt, user_prompt, current_model, result)

                    # Log structured observability data
                    if is_fallback:
                        logger.info(
                            "llm_call: completed (fallback) task=%s model=%s latency_ms=%d input_tokens=%d output_tokens=%d total_tokens=%d cached=%s",
                            task_name,
                            current_model,
                            elapsed_ms,
                            input_tokens,
                            output_tokens,
                            total_tokens,
                            cache is not None,
                        )
                    else:
                        logger.info(
                            "llm_call: completed task=%s model=%s latency_ms=%d input_tokens=%d output_tokens=%d total_tokens=%d cached=%s",
                            task_name,
                            current_model,
                            elapsed_ms,
                            input_tokens,
                            output_tokens,
                            total_tokens,
                            cache is not None,
                        )

                    return result
                except Exception as exc:
                    last_error = exc
                    exc_name = type(exc).__name__
                    exc_msg = str(exc)[:200]
                    if attempt == max_retries - 1:
                        logger.warning(
                            "llm_call: failed task=%s model=%s attempts=%d error=%s - %s",
                            task_name,
                            current_model,
                            max_retries,
                            exc_name,
                            exc_msg,
                        )
                        break
                    wait = 2 ** attempt
                    logger.warning(
                        "llm_call: retry task=%s model=%s attempt=%d/%d wait=%ds error=%s - %s",
                        task_name,
                        current_model,
                        attempt + 1,
                        max_retries,
                        wait,
                        exc_name,
                        exc_msg,
                    )
                    time.sleep(wait)

        # All models and retries failed
        if last_error is not None:
            logger.error(
                "llm_call: all models failed task=%s primary=%s fallbacks=%d",
                task_name,
                self.model,
                len(self.fallback_models),
            )
            raise last_error
        raise RuntimeError("llm_call failed without raising an exception")
