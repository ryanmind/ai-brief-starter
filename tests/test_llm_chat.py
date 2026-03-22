"""Tests for llm_chat with caching, failover, and observability logging."""
from __future__ import annotations

import json
from unittest.mock import Mock, MagicMock

import pytest
from src.models import NewsItem
from src.config import (
    REVIEW_PASS_THRESHOLD,
)
# Import directly from the module file using importlib
import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "src_llm",
    os.path.join(os.path.dirname(__file__), "..", "src", "llm.py")
)
src_llm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(src_llm)

llm_chat = src_llm.llm_chat
review_item_with_model = src_llm.review_item_with_model
review_items_with_multi_model = src_llm.review_items_with_multi_model


def test_llm_chat_primary_model_success(monkeypatch):
    """Test that llm_chat returns successfully when primary model works."""
    # Clear cache and disable caching for this test
    monkeypatch.setattr(src_llm, "_cache_instance", None)
    monkeypatch.setattr(src_llm, "LLM_CACHE_ENABLED", False)

    mock_client = Mock()
    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message.content = "Hello world"
    mock_response.choices = [mock_choice]
    mock_response.usage = None
    mock_client.chat.completions.create.return_value = mock_response

    result = llm_chat(
        client=mock_client,
        model="primary",
        system_prompt="system",
        user_prompt="user",
        max_tokens=100,
        fallback_models=["fallback1", "fallback2"],
        task_name="test",
    )

    assert result == "Hello world"
    mock_client.chat.completions.create.assert_called_once()
    # Verify it was called with primary model
    call_args = mock_client.chat.completions.create.call_args
    assert call_args[1]["model"] == "primary"


def test_llm_chat_fallback_after_primary_failure(monkeypatch):
    """Test that llm_chat falls back to secondary model when primary fails."""
    # Clear cache and disable caching for this test
    monkeypatch.setattr(src_llm, "_cache_instance", None)
    monkeypatch.setattr(src_llm, "LLM_CACHE_ENABLED", False)

    mock_client = Mock()

    # First call (primary) raises exception, second (fallback1) succeeds
    mock_success_response = Mock()
    mock_success_choice = Mock()
    mock_success_choice.message.content = "Fallback response"
    mock_success_response.choices = [mock_success_choice]
    mock_success_response.usage = None

    call_count = []
    def mock_create(**kwargs):
        call_count.append(kwargs["model"])
        if kwargs["model"] == "primary":
            raise RuntimeError("Primary down")
        return mock_success_response

    mock_client.chat.completions.create = mock_create

    result = llm_chat(
        client=mock_client,
        model="primary",
        system_prompt="system",
        user_prompt="user",
        max_tokens=100,
        max_retries=1,
        fallback_models=["fallback1", "fallback2"],
        task_name="test",
    )

    assert result == "Fallback response"
    assert call_count == ["primary", "fallback1"]


def test_llm_chat_all_models_fail_raises(monkeypatch):
    """Test that llm_chat raises when all models fail after all retries."""
    # Clear cache and disable caching for this test
    monkeypatch.setattr(src_llm, "_cache_instance", None)
    monkeypatch.setattr(src_llm, "LLM_CACHE_ENABLED", False)

    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = RuntimeError("All models down")

    with pytest.raises(RuntimeError, match="All models down"):
        llm_chat(
            client=mock_client,
            model="primary",
            system_prompt="system",
            user_prompt="user",
            max_retries=1,
            fallback_models=["fallback"],
            task_name="test",
        )


def test_llm_chat_returns_cached_result_when_available(monkeypatch, tmp_path):
    """Test that cached result is returned without calling API."""
    # Clear any existing cache
    monkeypatch.setattr(src_llm, "_cache_instance", None)
    monkeypatch.setattr(src_llm, "LLM_CACHE_ENABLED", True)
    # Use a temporary file for cache - monkeypatch in the imported module
    cache_path = tmp_path / "cache.db"
    monkeypatch.setattr(src_llm, "LLM_CACHE_PATH", str(cache_path))

    create_mock = Mock()
    create_mock.return_value = Mock(
        choices=[Mock(message=Mock(content="Fresh response"))],
        usage=None,
    )

    # Properly construct the mock chain
    mock_client = Mock()
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    mock_client.chat.completions.create = create_mock

    # First call - should go to API
    result1 = llm_chat(
        client=mock_client,
        model="model",
        system_prompt="system",
        user_prompt="user",
        task_name="test",
    )

    # Second call - should be cached
    result2 = llm_chat(
        client=mock_client,
        model="model",
        system_prompt="system",
        user_prompt="user",
        task_name="test",
    )

    assert result1 == result2
    assert result1 == "Fresh response"
    # Should only be called once due to caching
    assert create_mock.call_count == 1


def test_review_item_with_model_returns_valid_json(monkeypatch):
    """Test that review_item_with_model correctly parses JSON response."""
    mock_client = Mock()
    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message.content = json.dumps({
        "passed": True,
        "reason": "All checks passed",
        "issues": [],
    })
    mock_response.choices = [mock_choice]
    mock_response.usage = None
    mock_client.chat.completions.create.return_value = mock_response

    item = NewsItem(
        title="OpenAI发布新模型",
        link="https://example.com",
        summary="test",
        published="2026-03-21",
        brief="OpenAI发布了新模型",
        impact="这会影响行业格局",
        key_points=["发布新模型", "提升推理能力"],
    )

    result = review_item_with_model(mock_client, "model", item)

    assert result["passed"] is True
    assert "All checks" in result["reason"]
    assert isinstance(result["issues"], list)


def test_review_item_with_model_handles_string_passed_value(monkeypatch):
    """Test that review_item_with_model correctly handles string 'true'/'false'."""
    mock_client = Mock()
    mock_response = Mock()
    mock_choice = Mock()
    mock_choice.message.content = json.dumps({
        "passed": "false",
        "reason": "Failed check",
        "issues": ["Missing subject"],
    })
    mock_response.choices = [mock_choice]
    mock_response.usage = None
    mock_client.chat.completions.create.return_value = mock_response

    item = NewsItem(
        title="发布新版本",
        link="https://example.com",
        summary="test",
        published="2026-03-21",
    )

    result = review_item_with_model(mock_client, "model", item)

    assert result["passed"] is False
    assert len(result["issues"]) == 1


def test_review_item_with_model_fail_open_on_exception(monkeypatch):
    """Test that review_item_with_model defaults to passed=True on exception (fail-open)."""
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = RuntimeError("API timeout")

    item = NewsItem(
        title="OpenAI发布新模型",
        link="https://example.com",
        summary="test",
        published="2026-03-21",
    )

    result = review_item_with_model(mock_client, "model", item)

    # Fail-open philosophy: on exception, default to passed
    assert result["passed"] is True
    assert "审核出错" in result["reason"]


def test_review_items_with_multi_model_voting_meets_threshold(monkeypatch):
    """Test multi-model review when enough models pass."""
    monkeypatch.setattr("src.config.REVIEW_PASS_THRESHOLD", 2)

    mock_client = Mock()

    call_count = []
    def mock_review(*args, **kwargs):
        call_count.append(args[1])
        # First model passes, second model passes = meets threshold 2
        if len(call_count) == 1:
            return {"passed": True, "reason": "ok", "issues": []}
        if len(call_count) == 2:
            return {"passed": True, "reason": "ok", "issues": []}
        return {"passed": False, "reason": "no", "issues": []}

    monkeypatch.setattr(src_llm, "review_item_with_model", mock_review)

    items = [
        NewsItem(
            title="Test",
            link="https://example.com",
            summary="test",
            published="2026-03-21",
        )
    ]

    passed, stats = review_items_with_multi_model(items, "test-key")

    assert len(passed) == 1
    assert stats["passed"] == 1
    assert stats["rejected"] == 0


def test_review_items_with_multi_model_voting_below_threshold(monkeypatch):
    """Test multi-model review when not enough models pass."""
    monkeypatch.setattr("src.config.REVIEW_PASS_THRESHOLD", 2)

    mock_client = Mock()

    call_count = []
    def mock_review(*args, **kwargs):
        call_count.append(args[1])
        # Only one pass, one fail = below threshold 2
        if len(call_count) == 1:
            return {"passed": True, "reason": "ok", "issues": []}
        return {"passed": False, "reason": "no", "issues": []}

    monkeypatch.setattr(src_llm, "review_item_with_model", mock_review)
    monkeypatch.setattr("src.config.REVIEW_ENABLED", True)
    monkeypatch.setattr("src.config.get_review_models", lambda: ["model1", "model2"])

    items = [
        NewsItem(
            title="Test",
            link="https://example.com",
            summary="test",
            published="2026-03-21",
        )
    ]

    passed, stats = review_items_with_multi_model(items, "test-key")

    assert len(passed) == 0
    assert stats["passed"] == 0
    assert stats["rejected"] == 1
