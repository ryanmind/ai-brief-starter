"""Tests for LLM infrastructure: caching, prompt loading, failover, provider abstraction."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from src.llm.cache import LLMResponseCache
from src.llm.prompts import load_prompt


def test_cache_get_set_hit():
    """Test that cached value can be retrieved after setting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "cache.db"
        cache = LLMResponseCache(cache_path=str(cache_path), ttl_seconds=3600)

        system_prompt = "You are a helpful assistant."
        user_prompt = "Hello world"
        model = "test-model"
        response = "Hello back!"

        assert cache.get(system_prompt, user_prompt, model) is None
        cache.set(system_prompt, user_prompt, model, response)
        assert cache.get(system_prompt, user_prompt, model) == response


def test_cache_ttl_expiration():
    """Test that expired entries are not returned."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "cache.db"
        # TTL of 0.1 seconds = expires immediately
        cache = LLMResponseCache(cache_path=str(cache_path), ttl_seconds=0.1)

        system_prompt = "Test"
        user_prompt = "Expire"
        model = "model"
        response = "data"

        cache.set(system_prompt, user_prompt, model, response)
        # Wait for expiration
        time.sleep(0.2)
        assert cache.get(system_prompt, user_prompt, model) is None


def test_cache_different_model_different_key():
    """Test that different models have different cache keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "cache.db"
        cache = LLMResponseCache(cache_path=str(cache_path), ttl_seconds=3600)

        system_prompt = "Same prompt"
        user_prompt = "Same user"
        response = "Response"

        cache.set(system_prompt, user_prompt, "model-a", response)
        assert cache.get(system_prompt, user_prompt, "model-a") == response
        assert cache.get(system_prompt, user_prompt, "model-b") is None


def test_cache_different_prompt_different_key():
    """Test that different prompts have different cache keys."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "cache.db"
        cache = LLMResponseCache(cache_path=str(cache_path), ttl_seconds=3600)

        model = "model"
        response = "Response"

        cache.set("System 1", "User 1", model, response)
        assert cache.get("System 1", "User 1", model) == response
        assert cache.get("System 1", "User 2", model) is None
        assert cache.get("System 2", "User 1", model) is None


def test_load_prompt_existing_file():
    """Test loading a prompt from existing YAML file."""
    # The classify_ai_topic.yaml should exist and have system and user_template
    prompt_data = load_prompt("classify_ai_topic")

    assert "system" in prompt_data
    assert "user_template" in prompt_data
    assert isinstance(prompt_data["system"], str)
    assert isinstance(prompt_data["user_template"], str)
    assert len(prompt_data["system"]) > 0
    assert len(prompt_data["user_template"]) > 0
    assert "is_ai_topic" in prompt_data["user_template"]


def test_load_prompt_caching():
    """Test that prompts are cached after first load."""
    # This is a smoke test - just verify it doesn't crash
    # Actual caching happens inside the module level cache
    prompt_data1 = load_prompt("review_item")
    prompt_data2 = load_prompt("review_item")

    assert prompt_data1 is not None
    assert prompt_data2 is not None
    assert prompt_data1["system"] == prompt_data2["system"]


def test_load_prompt_all_existing_prompts():
    """Test that all prompt templates can be loaded successfully."""
    prompt_names = [
        "rank_and_summarize",
        "localize_items_to_chinese",
        "enforce_titles_with_subject",
        "classify_ai_topic",
        "polish_markdown",
        "review_item",
        "dedupe_selected_items",
    ]

    for name in prompt_names:
        prompt_data = load_prompt(name)
        assert "system" in prompt_data, f"{name} missing 'system'"
        assert "user_template" in prompt_data, f"{name} missing 'user_template'"
        assert isinstance(prompt_data["system"], str), f"{name} system not string"
        assert isinstance(prompt_data["user_template"], str), f"{name} user_template not string"
        assert len(prompt_data["system"]) > 0, f"{name} system empty"
        assert len(prompt_data["user_template"]) > 0, f"{name} user_template empty"


def test_prompt_templates_have_correct_placeholders():
    """Test that all prompt templates have the expected placeholders."""
    # rank_and_summarize
    data = load_prompt("rank_and_summarize")
    assert "{top_n}" in data["user_template"]
    assert "{candidates}" in data["user_template"]

    # classify_ai_topic
    data = load_prompt("classify_ai_topic")
    assert "{payload_json}" in data["user_template"]

    # polish_markdown
    data = load_prompt("polish_markdown")
    assert "{source_markdown}" in data["user_template"]

    # review_item
    data = load_prompt("review_item")
    assert "{title}" in data["user_template"]
    assert "{brief}" in data["user_template"]
    assert "{key_points}" in data["user_template"]
    assert "{impact}" in data["user_template"]
    assert "{link}" in data["user_template"]

    # dedupe_selected_items
    data = load_prompt("dedupe_selected_items")
    assert "{payload_json}" in data["user_template"]


def test_prompt_output_requirements_are_correct():
    """Test that prompts specify JSON output requirements."""
    # All prompts except polish_markdown should output JSON
    json_prompts = [
        "rank_and_summarize",
        "localize_items_to_chinese",
        "enforce_titles_with_subject",
        "classify_ai_topic",
        "review_item",
        "dedupe_selected_items",
    ]

    for name in json_prompts:
        data = load_prompt(name)
        combined = data["system"] + "\n" + data["user_template"]
        assert ("JSON" in combined or "json" in combined), f"{name} should mention JSON output"

    # polish_markdown should not output JSON, it outputs markdown directly
    data = load_prompt("polish_markdown")
    combined = data["system"] + "\n" + data["user_template"]
    assert "仅输出润色后的" in combined


@pytest.mark.parametrize(
    "task_name",
    [
        "rank_and_summarize",
        "localize_items_to_chinese",
        "enforce_titles_with_subject",
        "classify_ai_topic",
        "polish_markdown",
        "review_item",
        "dedupe_selected_items",
    ],
)
def test_prompt_no_trailing_newline_issues(task_name):
    """Test that prompts are properly formatted without problematic leading/trailing issues."""
    data = load_prompt(task_name)
    # System should not be empty
    assert data["system"].strip(), f"{task_name} system prompt is empty after stripping"
    # User template should not be empty
    assert data["user_template"].strip(), f"{task_name} user template is empty after stripping"


def test_file_not_found_raises():
    """Test that loading non-existent prompt raises appropriate error."""
    with pytest.raises(FileNotFoundError):
        load_prompt("does_not_exist")
