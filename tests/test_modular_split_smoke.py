from __future__ import annotations

import importlib
import importlib.util

import pytest

from scripts.report_quality_check import is_primary_source
from src.config import DEFAULT_PRIMARY_SOURCE_DOMAINS, DEFAULT_PRIMARY_X_HANDLES


def test_split_modules_are_importable():
    for module_name in ("src.text_utils", "src.filters", "src.report"):
        importlib.import_module(module_name)


def test_quality_check_primary_source_supports_markdown_x_link():
    allowed_domains = set(DEFAULT_PRIMARY_SOURCE_DOMAINS)
    allowed_handles = set(DEFAULT_PRIMARY_X_HANDLES)
    source = "[原文链接](https://x.com/openai/status/123)"
    assert is_primary_source(source, allowed_domains=allowed_domains, allowed_x_handles=allowed_handles)


def test_minimax_umbrella_sources_are_treated_as_primary():
    allowed_domains = set(DEFAULT_PRIMARY_SOURCE_DOMAINS)
    allowed_handles = set(DEFAULT_PRIMARY_X_HANDLES)

    assert is_primary_source(
        "https://x.com/MiniMax_AI/status/123",
        allowed_domains=allowed_domains,
        allowed_x_handles=allowed_handles,
    )
    assert is_primary_source(
        "https://x.com/Hailuo_AI/status/456",
        allowed_domains=allowed_domains,
        allowed_x_handles=allowed_handles,
    )
    assert is_primary_source(
        "https://talkie-ai.com/",
        allowed_domains=allowed_domains,
        allowed_x_handles=allowed_handles,
    )


def test_product_line_sources_from_other_vendors_are_treated_as_primary():
    allowed_domains = set(DEFAULT_PRIMARY_SOURCE_DOMAINS)
    allowed_handles = set(DEFAULT_PRIMARY_X_HANDLES)

    assert is_primary_source(
        "https://x.com/pika_labs/status/123",
        allowed_domains=allowed_domains,
        allowed_x_handles=allowed_handles,
    )
    assert is_primary_source(
        "https://x.com/perplexity_ai/status/456",
        allowed_domains=allowed_domains,
        allowed_x_handles=allowed_handles,
    )
    assert is_primary_source(
        "https://cursor.com/features",
        allowed_domains=allowed_domains,
        allowed_x_handles=allowed_handles,
    )


@pytest.mark.skipif(importlib.util.find_spec("requests") is None, reason="main.py depends on requests")
def test_main_exports_modular_functions():
    import main
    from src import feed as feed_module
    from src import report as report_module
    from src import text_utils as text_utils_module

    assert main.fetch_items is feed_module.fetch_items
    assert main.render_markdown is report_module.render_markdown
    assert main.build_contextual_title is text_utils_module.build_contextual_title
