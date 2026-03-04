from __future__ import annotations

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: F401 - Backward compatibility for tests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser  # noqa: F401 - Backward compatibility for tests monkeypatching main.feedparser
import requests  # noqa: F401 - Backward compatibility for tests monkeypatching main.requests

from scripts.report_quality_check import run_checks as run_quality_checks
from src.config import (
    FACT_OVERLAP_MIN,
    STRICT_FACT_MODE,
    int_env,
)
from src import feed as feed_module
from src import filters as filters_module
from src import llm as llm_module
from src import report as report_module
from src import text_utils as text_utils_module

logger = logging.getLogger(__name__)


# Backward-compatible exports: keep `main.py` API stable while logic lives in `src/*`.
clean_text = text_utils_module.clean_text
parse_time = text_utils_module.parse_time
normalize_host = text_utils_module.normalize_host
nitter_to_x_url = text_utils_module.nitter_to_x_url
extract_first_url = text_utils_module.extract_first_url
host_matches = text_utils_module.host_matches
extract_account_from_url = text_utils_module.extract_account_from_url
contains_second_hand_cue = text_utils_module.contains_second_hand_cue
title_looks_incomplete = text_utils_module.title_looks_incomplete
extract_source_subject = text_utils_module.extract_source_subject
title_needs_subject_context = text_utils_module.title_needs_subject_context
build_contextual_title = text_utils_module.build_contextual_title
pick_preferred_title = text_utils_module.pick_preferred_title
title_has_explicit_subject = text_utils_module.title_has_explicit_subject
build_subject_guaranteed_title = text_utils_module.build_subject_guaranteed_title
key_point_dedupe_key = text_utils_module.key_point_dedupe_key
normalize_key_point_text = text_utils_module.normalize_key_point_text
split_key_point_candidates = text_utils_module.split_key_point_candidates
normalize_key_points = text_utils_module.normalize_key_points
build_default_key_points = text_utils_module.build_default_key_points
ensure_sentence_end = text_utils_module.ensure_sentence_end
collapse_duplicate_punctuation = text_utils_module.collapse_duplicate_punctuation
is_placeholder_text = text_utils_module.is_placeholder_text
sanitize_generated_clause = text_utils_module.sanitize_generated_clause
clean_generated_text = text_utils_module.clean_generated_text
shorten_for_highlight = text_utils_module.shorten_for_highlight
sentence_candidates = text_utils_module.sentence_candidates
normalize_for_compare = text_utils_module.normalize_for_compare
extract_numbers = text_utils_module.extract_numbers
has_unseen_numbers = text_utils_module.has_unseen_numbers
fact_overlap_ratio = text_utils_module.fact_overlap_ratio
extractive_brief = text_utils_module.extractive_brief
build_detail_from_summary = text_utils_module.build_detail_from_summary
fix_item_detail = text_utils_module.fix_item_detail
fix_items_detail = text_utils_module.fix_items_detail
extract_urls = text_utils_module.extract_urls
extract_numeric_tokens = text_utils_module.extract_numeric_tokens
finalize_key_points = text_utils_module.finalize_key_points
contains_second_hand_domain = text_utils_module.contains_second_hand_domain
build_fallback_impact = text_utils_module.build_fallback_impact
normalize_link_for_dedupe = text_utils_module.normalize_link_for_dedupe
normalize_title_for_dedupe = text_utils_module.normalize_title_for_dedupe
item_dedupe_fingerprints = text_utils_module.item_dedupe_fingerprints
source_bucket_key = text_utils_module.source_bucket_key
strip_markdown_fence = text_utils_module.strip_markdown_fence
polish_result_is_safe = text_utils_module.polish_result_is_safe


# Keep FACT_OVERLAP_MIN / STRICT_FACT_MODE monkeypatch behavior from historical tests.
def sanitize_item_factuality(item: dict[str, str]) -> dict[str, str]:
    text_utils_module.FACT_OVERLAP_MIN = FACT_OVERLAP_MIN
    text_utils_module.STRICT_FACT_MODE = STRICT_FACT_MODE
    return text_utils_module.sanitize_item_factuality(item)


def sanitize_items_factuality(items: list[dict[str, str]]) -> list[dict[str, str]]:
    text_utils_module.FACT_OVERLAP_MIN = FACT_OVERLAP_MIN
    text_utils_module.STRICT_FACT_MODE = STRICT_FACT_MODE
    return text_utils_module.sanitize_items_factuality(items)


_X_RESERVED_HANDLES = feed_module._X_RESERVED_HANDLES
_twitterapi_io_cache = feed_module._twitterapi_io_cache
_twitterapi_io_cache_lock = feed_module._twitterapi_io_cache_lock
clear_twitter_caches = feed_module.clear_twitter_caches
is_twitterapi_io_enabled = feed_module.is_twitterapi_io_enabled
twitterapi_io_fallback_ready = feed_module.twitterapi_io_fallback_ready
extract_x_handle_from_source = feed_module.extract_x_handle_from_source
fetch_from_twitterapi_io = feed_module.fetch_from_twitterapi_io
load_sources = feed_module.load_sources
probe_nitter_bases = feed_module.probe_nitter_bases
parse_github_changelog_feed = feed_module.parse_github_changelog_feed
github_feed_fallback_urls = feed_module.github_feed_fallback_urls
normalize_link_for_source = feed_module.normalize_link_for_source
expand_source_urls = feed_module.expand_source_urls
_fetch_single_source = feed_module._fetch_single_source
fetch_items = feed_module.fetch_items

collect_report_history_fingerprints = filters_module.collect_report_history_fingerprints
load_recent_history_fingerprints = filters_module.load_recent_history_fingerprints
load_history_state = filters_module.load_history_state
history_state_fingerprints = filters_module.history_state_fingerprints
update_history_state = filters_module.update_history_state
save_history_state = filters_module.save_history_state
filter_items_by_history = filters_module.filter_items_by_history
is_github_commit_link = filters_module.is_github_commit_link
get_primary_rejection_reason = filters_module.get_primary_rejection_reason
is_primary_item = filters_module.is_primary_item
filter_primary_items = filters_module.filter_primary_items
filter_primary_items_with_stats = filters_module.filter_primary_items_with_stats
filter_ai_topic_items_with_stats = filters_module.filter_ai_topic_items_with_stats
apply_source_limits = filters_module.apply_source_limits

llm_chat = llm_module.llm_chat
extract_json = llm_module.extract_json
fallback_selection = llm_module.fallback_selection
backfill_selected_items = llm_module.backfill_selected_items
rank_and_summarize = llm_module.rank_and_summarize
localize_items_to_chinese = llm_module.localize_items_to_chinese
enforce_titles_with_subject = llm_module.enforce_titles_with_subject
classify_ai_topic_items_with_llm = llm_module.classify_ai_topic_items_with_llm
polish_markdown_with_llm = llm_module.polish_markdown_with_llm

check_category_balance = report_module.check_category_balance
render_markdown = report_module.render_markdown
prepend_quality_review_banner = report_module.prepend_quality_review_banner


_LEGACY_PIPELINE_FUNCTIONS = {
    "load_sources": load_sources,
    "fetch_items": fetch_items,
    "filter_primary_items_with_stats": filter_primary_items_with_stats,
    "filter_ai_topic_items_with_stats": filter_ai_topic_items_with_stats,
    "apply_source_limits": apply_source_limits,
    "filter_items_by_history": filter_items_by_history,
    "rank_and_summarize": rank_and_summarize,
    "localize_items_to_chinese": localize_items_to_chinese,
    "enforce_titles_with_subject": enforce_titles_with_subject,
    "check_category_balance": check_category_balance,
    "render_markdown": render_markdown,
    "polish_markdown_with_llm": polish_markdown_with_llm,
}


def _resolve_pipeline_callable(name: str, modular_callable: Any) -> Any:
    current_callable = globals().get(name)
    if current_callable is None:
        return modular_callable
    if current_callable is _LEGACY_PIPELINE_FUNCTIONS.get(name):
        return modular_callable
    return current_callable


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    qwen_api_key = os.getenv("QWEN_API_KEY", "").strip()
    if not qwen_api_key:
        raise RuntimeError("QWEN_API_KEY 未设置")

    qwen_model = os.getenv("QWEN_MODEL", "qwen-flash")
    max_items = int_env("MAX_ITEMS", 120, min_value=10, max_value=500)
    top_n = int_env("TOP_N", 20, min_value=5, max_value=100)
    fetch_hours = int_env("FETCH_HOURS", 24, min_value=1, max_value=168)
    per_source_items = int_env("PER_SOURCE_ITEMS", 30, min_value=5, max_value=200)
    history_dedupe_days = int_env("HISTORY_DEDUP_DAYS", 2, min_value=0, max_value=30)
    history_state_max_days = int_env("HISTORY_STATE_MAX_DAYS", 14, min_value=1, max_value=90)
    quality_check_fail_open_requested = os.getenv("QUALITY_CHECK_FAIL_OPEN", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    quality_check_fail_open = True
    if not quality_check_fail_open_requested:
        logger.warning("QUALITY_CHECK_FAIL_OPEN=0 已被忽略：质量检测缺陷仅告警，不再中断发布流程。")

    load_sources_fn = _resolve_pipeline_callable("load_sources", feed_module.load_sources)
    fetch_items_fn = _resolve_pipeline_callable("fetch_items", feed_module.fetch_items)
    filter_primary_items_with_stats_fn = _resolve_pipeline_callable(
        "filter_primary_items_with_stats",
        filters_module.filter_primary_items_with_stats,
    )
    filter_ai_topic_items_with_stats_fn = _resolve_pipeline_callable(
        "filter_ai_topic_items_with_stats",
        filters_module.filter_ai_topic_items_with_stats,
    )
    apply_source_limits_fn = _resolve_pipeline_callable("apply_source_limits", filters_module.apply_source_limits)
    filter_items_by_history_fn = _resolve_pipeline_callable(
        "filter_items_by_history",
        filters_module.filter_items_by_history,
    )
    rank_and_summarize_fn = _resolve_pipeline_callable("rank_and_summarize", llm_module.rank_and_summarize)
    localize_items_to_chinese_fn = _resolve_pipeline_callable(
        "localize_items_to_chinese",
        llm_module.localize_items_to_chinese,
    )
    enforce_titles_with_subject_fn = _resolve_pipeline_callable(
        "enforce_titles_with_subject",
        llm_module.enforce_titles_with_subject,
    )
    check_category_balance_fn = _resolve_pipeline_callable(
        "check_category_balance",
        report_module.check_category_balance,
    )
    render_markdown_fn = _resolve_pipeline_callable("render_markdown", report_module.render_markdown)
    polish_markdown_with_llm_fn = _resolve_pipeline_callable(
        "polish_markdown_with_llm",
        llm_module.polish_markdown_with_llm,
    )

    report_dir = Path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    quality_metrics_path = report_dir / "quality_metrics.json"
    high_risk_path = report_dir / "high_risk_items.md"
    history_state_path = Path(os.getenv("HISTORY_STATE_PATH", str(report_dir / "history_index.json")))
    history_state = load_history_state(history_state_path)
    history_fingerprints = load_recent_history_fingerprints(report_dir=report_dir, lookback_days=history_dedupe_days)
    history_fingerprints.update(history_state_fingerprints(history_state, lookback_days=history_dedupe_days))

    sources = load_sources_fn("sources.txt")
    fetched_items = fetch_items_fn(sources=sources, hours=fetch_hours, per_source=per_source_items)

    def prepare_items(
        raw_items: list[dict[str, str]],
    ) -> tuple[list[dict[str, str]], dict[str, int], dict[str, int], dict[str, int], int, dict[str, int]]:
        filtered_items, rejected_stats = filter_primary_items_with_stats_fn(raw_items)
        ai_topic_items, ai_topic_stats = filter_ai_topic_items_with_stats_fn(
            filtered_items,
            qwen_api_key=qwen_api_key,
            qwen_model=qwen_model,
        )
        diversified_items, diversity_stats = apply_source_limits_fn(ai_topic_items)
        history_filtered_items, history_dropped = filter_items_by_history_fn(diversified_items, history_fingerprints)
        stage_stats = {
            "after_primary": len(filtered_items),
            "after_ai_topic": len(ai_topic_items),
            "after_source_limit": len(diversified_items),
            "after_history_dedupe": len(history_filtered_items),
        }
        return (
            history_filtered_items[:max_items],
            rejected_stats,
            ai_topic_stats,
            diversity_stats,
            history_dropped,
            stage_stats,
        )

    items, rejected_stats, ai_topic_stats, diversity_stats, history_dropped, stage_stats = prepare_items(fetched_items)

    rejected_count = sum(rejected_stats.values())
    logger.info(
        "items fetched=%s rejected=%s history_dropped=%s kept=%s top_n=%s",
        len(fetched_items),
        rejected_count,
        history_dropped,
        len(items),
        top_n,
    )
    if rejected_stats:
        logger.info("primary filter rejected reasons=%s", json.dumps(rejected_stats, ensure_ascii=False))
    if ai_topic_stats:
        logger.info("ai-topic filter rejected reasons=%s", json.dumps(ai_topic_stats, ensure_ascii=False))
    if diversity_stats:
        logger.info("source limit dropped reasons=%s", json.dumps(diversity_stats, ensure_ascii=False))
    if not items:
        raise RuntimeError("未抓到一手资讯，请检查 sources.txt 或放宽 STRICT_PRIMARY_ONLY 配置")

    selected = rank_and_summarize_fn(items=items, qwen_api_key=qwen_api_key, qwen_model=qwen_model, top_n=top_n)
    selected = localize_items_to_chinese_fn(items=selected, qwen_api_key=qwen_api_key, qwen_model=qwen_model)
    selected = enforce_titles_with_subject_fn(items=selected, qwen_api_key=qwen_api_key, qwen_model=qwen_model)
    if not selected:
        raise RuntimeError("无内容：模型筛选后最终条目数为 0")

    check_category_balance_fn(selected)
    draft_report_path = report_dir / "latest.draft.md"
    markdown = render_markdown_fn(selected)
    markdown = polish_markdown_with_llm_fn(
        markdown=markdown,
        qwen_api_key=qwen_api_key,
        qwen_model=qwen_model,
    )
    draft_report_path.write_text(markdown, encoding="utf-8")

    quality_gate_opened = False
    quality_code = run_quality_checks(
        path=draft_report_path,
        autofix=True,
        metrics_output=quality_metrics_path,
        high_risk_output=high_risk_path,
    )
    if quality_code != 0:
        quality_gate_opened = True
        logger.error("自动修复后质检仍未通过：流程不中断，将在飞书通知中提示缺陷。")
    else:
        second_quality_code = run_quality_checks(path=draft_report_path, autofix=False)
        if second_quality_code != 0:
            quality_gate_opened = True
            logger.error("二次质检失败：流程不中断，将在飞书通知中提示缺陷。")
    markdown = draft_report_path.read_text(encoding="utf-8")
    if quality_gate_opened:
        markdown = prepend_quality_review_banner(markdown)
    final_item_count = markdown.count("\n### ")
    if final_item_count <= 0:
        raise RuntimeError("无内容：最终报告条目数为 0，停止发布")

    history_state = update_history_state(
        state=history_state,
        run_date=datetime.now(),
        items=selected,
        keep_days=history_state_max_days,
    )
    save_history_state(path=history_state_path, state=history_state)

    daily = report_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    latest = report_dir / "latest.md"
    daily.write_text(markdown, encoding="utf-8")
    latest.write_text(markdown, encoding="utf-8")
    if draft_report_path.exists():
        draft_report_path.unlink()

    quality_metrics: dict[str, Any] = {}
    if quality_metrics_path.exists():
        try:
            quality_metrics = json.loads(quality_metrics_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("quality metrics parse failed: %s", exc)
            quality_metrics = {}

    combined_failure_reasons: dict[str, int] = {}
    for reason_stats in (rejected_stats, ai_topic_stats, diversity_stats):
        for key, count in reason_stats.items():
            combined_failure_reasons[key] = combined_failure_reasons.get(key, 0) + int(count)
    if history_dropped > 0:
        combined_failure_reasons["history_dedup"] = history_dropped
    quality_failure_reasons = quality_metrics.get("failure_reasons", {})
    if isinstance(quality_failure_reasons, dict):
        for key, count in quality_failure_reasons.items():
            try:
                count_int = int(count)
            except (TypeError, ValueError):
                continue
            combined_failure_reasons[key] = combined_failure_reasons.get(key, 0) + count_int

    top_failure_reasons = sorted(combined_failure_reasons.items(), key=lambda item: item[1], reverse=True)[:5]
    merged_metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fetched_count": len(fetched_items),
        "filtered_count": max(len(fetched_items) - len(items), 0),
        "repaired_count": int(quality_metrics.get("repaired_count", 0)) if isinstance(quality_metrics, dict) else 0,
        "final_item_count": final_item_count,
        "quality_fail_open_enabled": quality_check_fail_open,
        "quality_gate_opened": quality_gate_opened,
        "stage_counts": stage_stats,
        "failure_reasons_top": [{"reason": reason, "count": count} for reason, count in top_failure_reasons],
        "quality_check": quality_metrics,
    }
    quality_metrics_path.write_text(json.dumps(merged_metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"done: {daily}")


if __name__ == "__main__":
    main()
