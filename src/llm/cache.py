"""LLM response cache to avoid redundant API calls and reduce token cost.

This module provides a file-based cache that stores complete LLM responses
keyed by a hash of (system_prompt + user_prompt + model). Cache entries expire
after a configurable TTL (default 7 days).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


class LLMResponseCache:
    """File-based cache for LLM responses.

    Caches responses based on the full content of the prompt and model,
    so identical requests will hit the cache and avoid redundant API calls.
    """

    def __init__(self, cache_path: str, ttl_seconds: int):
        """Initialize the cache.

        Args:
            cache_path: Path to the JSON cache file
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.cache_path = cache_path
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}
        self._loaded = False
        self._dirty = False

    def _compute_key(self, system_prompt: str, user_prompt: str, model: str) -> str:
        """Compute a cache key from the request contents.

        The key is a SHA-256 hash of the concatenated inputs.
        """
        content = f"{model}\n{system_prompt}\n{user_prompt}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _load_cache(self) -> None:
        """Load cache from disk if not already loaded."""
        if self._loaded:
            return

        if not os.path.exists(self.cache_path):
            self._cache = {}
            self._loaded = True
            self._dirty = False
            return

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cache = data if isinstance(data, dict) else {}
            # Clean up expired entries on load (in-memory only, no write)
            expired_count = self._cleanup()
            if expired_count > 0:
                logger.debug("Cleaned up %d expired cache entries", expired_count)
        except (json.JSONDecodeError, IOError) as exc:
            logger.warning("Failed to load LLM cache, starting with empty cache: %s", exc)
            self._cache = {}

        self._loaded = True
        self._dirty = False

    def _cleanup(self) -> int:
        """Remove expired cache entries. Returns the number of entries removed."""
        now = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.get("timestamp", 0) + self.ttl_seconds < now
        ]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            self._dirty = True
        return len(expired_keys)

    def _save_cache(self) -> None:
        """Save the current cache to disk."""
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except IOError as exc:
            logger.warning("Failed to save LLM cache: %s", exc)

    def get(self, system_prompt: str, user_prompt: str, model: str) -> str | None:
        """Get a cached response if it exists and is not expired.

        Returns None if the cache entry doesn't exist or is expired.
        """
        self._load_cache()
        key = self._compute_key(system_prompt, user_prompt, model)
        entry = self._cache.get(key)
        if entry is None:
            return None

        now = time.time()
        if entry.get("timestamp", 0) + self.ttl_seconds < now:
            del self._cache[key]
            self._dirty = True
            return None

        return entry.get("response")

    def set(self, system_prompt: str, user_prompt: str, model: str, response: str) -> None:
        """Store a response in the cache.

        Does not flush to disk immediately; call flush() to persist.
        """
        self._load_cache()
        key = self._compute_key(system_prompt, user_prompt, model)
        self._cache[key] = {
            "timestamp": int(time.time()),
            "response": response,
        }
        self._dirty = True

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache = {}
        self._loaded = True
        self._dirty = False
        self._save_cache()
        logger.info("Cleared LLM cache")

    def flush(self) -> None:
        """Write any pending changes to disk if the cache is dirty."""
        if self._dirty:
            self._save_cache()
            self._dirty = False

    def stats(self) -> tuple[int, int]:
        """Return (total_entries, expired_entries) count."""
        self._load_cache()
        now = time.time()
        expired = sum(
            1 for entry in self._cache.values()
            if entry.get("timestamp", 0) + self.ttl_seconds < now
        )
        return len(self._cache), expired
