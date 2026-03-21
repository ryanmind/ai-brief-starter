"""Base LLM client abstract interface.

This module defines the contract that all LLM provider implementations
must satisfy to be compatible with the AI Brief pipeline.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMClient(ABC):
    """Abstract base interface for LLM API clients.

    Implementations must support chat completion requests with
    system and user prompts and return a string response.
    """

    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        task_name: str = "unknown",
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
    ) -> str:
        """Send a chat completion request to the LLM.

        Args:
            system_prompt: System instruction for the model
            user_prompt: User input/request
            task_name: Name of the task for logging and observability
            max_tokens: Maximum tokens in the response (optional)
            max_retries: Maximum retry attempts on failure (default: 3)

        Returns:
            The model's response text, trimmed of leading/trailing whitespace

        Raises:
            Exception: If all retry attempts fail
        """
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this provider for logging and debugging."""
        ...
