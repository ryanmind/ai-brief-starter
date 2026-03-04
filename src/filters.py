"""Filters: primary source, AI topic, source limits, and history deduplication."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from src.config import (
    DEFAULT_PRIMARY_SOURCE_DOMAINS,
    DEFAULT_PRIMARY_X_HANDLES,
    DEFAULT_SECOND_HAND_DOMAINS,
    DEFAULT_AI_TOPIC_KEYWORDS,
    X_HOSTS,
    int_env,
    parse_csv_env,
)
from src.models import NewsItem
from src.text_utils import (
    clean_text,
    contains_second_hand_cue,
    contains_second_hand_domain,
    extract_account_from_url,
    extract_first_url,
    host_matches,
    item_dedupe_fingerprints,
    normalize_host,
    normalize_link_for_dedupe,
    normalize_title_for_dedupe,
    source_bucket_key,
)

logger = logging.getLogger(__name__)


REPORT_ITEM_TITLE_PATTERN = re.compile(r"^###\s+\d+[\.\)、]\s*(.*\S)")
REPORT_ITEM_SOURCE_PATTERN = re.compile(
    r"^\*{0,2}(?:来源|source)\*{0,2}\s*[：:]\s*(.*\S)",
    flags=re.IGNORECASE,
)


def collect_report_history_fingerprints(report_path: Path) -> set[str]:
    fingerprints: set[str] = set()
    current_title = ""
    try:
        lines = report_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("read report failed, skip history dedupe: %s (%s)", report_path, exc)
        return fingerprints

    for raw_line in lines:
        line = raw_line.strip()
        title_match = REPORT_ITEM_TITLE_PATTERN.match(line)
        if title_match:
            current_title = clean_text(title_match.group(1))
            continue

        source_match = REPORT_ITEM_SOURCE_PATTERN.match(line)
        if not source_match:
            continue
        source = extract_first_url(source_match.group(1)) or clean_text(source_match.group(1))
        if source:
            source_key = normalize_link_for_dedupe(source)
            if source_key:
                fingerprints.add(f"l:{source_key}")
        if current_title:
            title_key = normalize_title_for_dedupe(current_title)
            if title_key:
                fingerprints.add(f"t:{title_key}")
        current_title = ""

    return fingerprints


def load_recent_history_fingerprints(report_dir: Path, lookback_days: int) -> set[str]:
    if lookback_days <= 0 or not report_dir.exists():
        return set()

    history_keys: set[str] = set()
    today = datetime.now().date()
    for offset in range(1, lookback_days + 1):
        target = today - timedelta(days=offset)
        report_path = report_dir / f"{target.strftime('%Y-%m-%d')}.md"
        if report_path.exists():
            history_keys.update(collect_report_history_fingerprints(report_path))
    return history_keys


def load_history_state(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("history state parse failed: %s (%s)", path, exc)
        return {}

    if not isinstance(payload, dict):
        return {}
    days = payload.get("days")
    if not isinstance(days, dict):
        return {}

    state: dict[str, list[str]] = {}
    for date_key, values in days.items():
        if not isinstance(date_key, str) or not isinstance(values, list):
            continue
        fingerprints = [str(value).strip() for value in values if str(value).strip()]
        if fingerprints:
            state[date_key] = fingerprints
    return state


def history_state_fingerprints(state: dict[str, list[str]], lookback_days: int) -> set[str]:
    if lookback_days <= 0:
        return set()
    today = datetime.now().date()
    keys: set[str] = set()
    for offset in range(1, lookback_days + 1):
        date_key = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        keys.update(state.get(date_key, []))
    return keys


def update_history_state(
    state: dict[str, list[str]],
    run_date: datetime,
    items: list[NewsItem] | list[dict[str, str]],
    keep_days: int,
) -> dict[str, list[str]]:
    updated: dict[str, list[str]] = {key: list(values) for key, values in state.items()}
    date_key = run_date.strftime("%Y-%m-%d")
    fingerprints: set[str] = set(updated.get(date_key, []))
    for item in items:
        fingerprints.update(item_dedupe_fingerprints(item))
    updated[date_key] = sorted(fingerprints)

    if keep_days <= 0:
        keep_days = 1
    cutoff = run_date.date() - timedelta(days=keep_days - 1)
    cleaned: dict[str, list[str]] = {}
    for key, values in updated.items():
        try:
            parsed_date = datetime.strptime(key, "%Y-%m-%d").date()
        except ValueError:
            continue
        if parsed_date >= cutoff and values:
            cleaned[key] = values
    return cleaned


def save_history_state(path: Path, state: dict[str, list[str]]) -> None:
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "days": {key: state[key] for key in sorted(state.keys(), reverse=True)},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def filter_items_by_history(
    items: list[NewsItem] | list[dict[str, str]],
    history_fingerprints: set[str],
) -> tuple[list[NewsItem], int]:
    if not history_fingerprints:
        # Convert dicts to NewsItem if needed
        if items and isinstance(items[0], dict):
            items = [NewsItem.from_dict(item) for item in items]
        return items, 0

    # Convert dicts to NewsItem if needed
    if items and isinstance(items[0], dict):
        items = [NewsItem.from_dict(item) for item in items]

    kept: list[NewsItem] = []
    dropped = 0
    for item in items:
        fingerprints = item_dedupe_fingerprints(item)
        if fingerprints and history_fingerprints.intersection(fingerprints):
            dropped += 1
            continue
        kept.append(item)

    return kept, dropped


def is_github_commit_link(url: str) -> bool:
    parsed = urlparse(url)
    host = normalize_host(parsed.netloc or "")
    if host != "github.com":
        return False
    path = parsed.path.strip("/")
    return bool(re.match(r"[^/]+/[^/]+/commit/[0-9a-f]{7,40}$", path, flags=re.IGNORECASE))


def get_primary_rejection_reason(
    item: NewsItem | dict[str, str],
    allowed_domains: set[str],
    allowed_x_handles: set[str],
    blocked_domains: set[str] | None = None,
) -> str | None:
    # Handle both NewsItem and dict for backward compatibility
    if isinstance(item, dict):
        link = (item.get("link", "") or "").strip()
        title = item.get("title", "")
        summary = item.get("summary", "")
    else:
        link = (item.link or "").strip()
        title = item.title
        summary = item.summary

    if not link:
        return "missing_link"
    if is_github_commit_link(link):
        return "github_commit_link"

    parsed = urlparse(link)
    host = normalize_host(parsed.netloc or "")
    if not host:
        return "missing_host"

    if host in X_HOSTS:
        account = extract_account_from_url(link)
        if not account:
            return "missing_x_account"
        if allowed_x_handles and account not in allowed_x_handles:
            return "non_primary_x_handle"
    else:
        if not host_matches(host, allowed_domains):
            return "non_primary_domain"

    evidence = f"{clean_text(title)} {clean_text(summary)}".strip()
    if evidence and contains_second_hand_cue(evidence):
        return "second_hand_cue"

    if blocked_domains is None:
        blocked_domains = parse_csv_env("SECOND_HAND_DOMAINS", DEFAULT_SECOND_HAND_DOMAINS)
    if evidence and contains_second_hand_domain(evidence, blocked_domains):
        return "second_hand_domain"

    return None


def is_primary_item(
    item: NewsItem | dict[str, str],
    allowed_domains: set[str],
    allowed_x_handles: set[str],
) -> bool:
    return get_primary_rejection_reason(
        item=item,
        allowed_domains=allowed_domains,
        allowed_x_handles=allowed_x_handles,
    ) is None


def filter_primary_items(items: list[NewsItem] | list[dict[str, str]]) -> list[NewsItem]:
    filtered, _ = filter_primary_items_with_stats(items)
    return filtered


def filter_primary_items_with_stats(items: list[NewsItem] | list[dict[str, str]]) -> tuple[list[NewsItem], dict[str, int]]:
    strict_primary_only = os.getenv("STRICT_PRIMARY_ONLY", "1").strip().lower()
    if strict_primary_only in {"0", "false", "no", "off"}:
        # Convert dicts to NewsItem if needed
        if items and isinstance(items[0], dict):
            items = [NewsItem.from_dict(item) for item in items]
        return items, {"strict_mode_disabled": len(items)}

    # Convert dicts to NewsItem if needed
    if items and isinstance(items[0], dict):
        items = [NewsItem.from_dict(item) for item in items]

    allowed_domains = parse_csv_env("PRIMARY_SOURCE_DOMAINS", DEFAULT_PRIMARY_SOURCE_DOMAINS)
    allowed_x_handles = parse_csv_env("PRIMARY_X_HANDLES", DEFAULT_PRIMARY_X_HANDLES)
    blocked_domains = parse_csv_env("SECOND_HAND_DOMAINS", DEFAULT_SECOND_HAND_DOMAINS)
    filtered: list[NewsItem] = []
    rejected_stats: dict[str, int] = {}

    for item in items:
        reason = get_primary_rejection_reason(
            item=item,
            allowed_domains=allowed_domains,
            allowed_x_handles=allowed_x_handles,
            blocked_domains=blocked_domains,
        )
        if reason is None:
            filtered.append(item)
            continue
        rejected_stats[reason] = rejected_stats.get(reason, 0) + 1

    return filtered, rejected_stats


def filter_ai_topic_items_with_stats(
    items: list[NewsItem] | list[dict[str, str]],
    qwen_api_key: str = "",
    qwen_model: str = "",
) -> tuple[list[NewsItem], dict[str, int]]:
    from src.llm import classify_ai_topic_items_with_llm  # avoid circular import

    strict_ai_topic_only = os.getenv("STRICT_AI_TOPIC_ONLY", "1").strip().lower()
    if strict_ai_topic_only in {"0", "false", "no", "off"}:
        # Convert dicts to NewsItem if needed
        if items and isinstance(items[0], dict):
            items = [NewsItem.from_dict(item) for item in items]
        return items, {"strict_mode_disabled": len(items)}

    if not items:
        return [], {}

    # Convert dicts to NewsItem if needed
    if items and isinstance(items[0], dict):
        items = [NewsItem.from_dict(item) for item in items]

    api_key = qwen_api_key.strip() if qwen_api_key else os.getenv("QWEN_API_KEY", "").strip()
    model = qwen_model.strip() if qwen_model else os.getenv("QWEN_MODEL", "qwen-flash").strip()
    if not api_key:
        logger.warning("STRICT_AI_TOPIC_ONLY=1 but QWEN_API_KEY missing, keep all items as fallback")
        return items, {"llm_unavailable_keep_all": len(items)}

    keywords = parse_csv_env("AI_TOPIC_KEYWORDS", DEFAULT_AI_TOPIC_KEYWORDS)
    decisions, llm_stats = classify_ai_topic_items_with_llm(
        items=items,
        qwen_api_key=api_key,
        qwen_model=model,
        keywords=keywords,
    )
    if len(decisions) != len(items):
        logger.warning("ai-topic llm returned mismatched decisions, keep all items as fallback")
        return items, {"llm_invalid_result_keep_all": len(items)}

    filtered: list[NewsItem] = []
    rejected = 0
    for item, decision in zip(items, decisions):
        if decision is False:
            rejected += 1
            continue
        filtered.append(item)

    stats = {k: v for k, v in llm_stats.items() if v > 0}
    if rejected > 0:
        stats["non_ai_topic"] = rejected

    if not filtered and items:
        logger.warning("ai-topic llm rejected all items, keep all as fallback to avoid empty output")
        stats["llm_all_rejected_keep_all"] = len(items)
        return items, stats

    return filtered, stats


def apply_source_limits(items: list[NewsItem] | list[dict[str, str]]) -> tuple[list[NewsItem], dict[str, int]]:
    per_domain_limit = int_env("PER_DOMAIN_LIMIT", 4, min_value=0, max_value=50)
    arxiv_max_items = int_env("ARXIV_MAX_ITEMS", 4, min_value=0, max_value=50)

    if per_domain_limit <= 0 and arxiv_max_items <= 0:
        # Convert dicts to NewsItem if needed
        if items and isinstance(items[0], dict):
            items = [NewsItem.from_dict(item) for item in items]
        return items, {}

    # Convert dicts to NewsItem if needed
    if items and isinstance(items[0], dict):
        items = [NewsItem.from_dict(item) for item in items]

    kept: list[NewsItem] = []
    bucket_counts: dict[str, int] = {}
    arxiv_count = 0
    dropped: dict[str, int] = {}

    for item in items:
        link = item.link
        host = normalize_host(urlparse(link).netloc or "")
        bucket = source_bucket_key(link)
        is_arxiv = host in {"arxiv.org", "export.arxiv.org"}

        if is_arxiv and arxiv_max_items > 0 and arxiv_count >= arxiv_max_items:
            dropped["arxiv_limit"] = dropped.get("arxiv_limit", 0) + 1
            continue

        if per_domain_limit > 0 and bucket and bucket_counts.get(bucket, 0) >= per_domain_limit:
            dropped["source_bucket_limit"] = dropped.get("source_bucket_limit", 0) + 1
            continue

        kept.append(item)
        if bucket:
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        if is_arxiv:
            arxiv_count += 1

    return kept, dropped
