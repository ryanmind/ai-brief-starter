from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import feedparser
from dateutil import parser as dtparser
from openai import OpenAI


def int_env(name: str, default: int, min_value: int = 1, max_value: int = 1000) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min_value, min(max_value, value))


def float_env(name: str, default: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(min_value, min(max_value, value))


BRIEF_MAX_CHARS = int_env("BRIEF_MAX_CHARS", 160, min_value=40, max_value=400)
IMPACT_MAX_CHARS = int_env("IMPACT_MAX_CHARS", 140, min_value=40, max_value=320)
DETAIL_MAX_CHARS = int_env("DETAIL_MAX_CHARS", 260, min_value=80, max_value=800)
DETAIL_MIN_CHARS = int_env("DETAIL_MIN_CHARS", 48, min_value=20, max_value=200)
STRICT_FACT_MODE = os.getenv("STRICT_FACT_MODE", "1").strip().lower() not in {"0", "false", "no", "off"}
FACT_OVERLAP_MIN = float_env("FACT_OVERLAP_MIN", 0.55, min_value=0.1, max_value=1.0)
TITLE_MAX_CHARS = 50
KEY_POINTS_MAX_COUNT = 3
KEY_POINTS_MIN_COUNT = 2
KEY_POINT_MAX_CHARS = 28
KEY_POINT_MIN_CHARS = 4
TITLE_INCOMPLETE_PREFIXES = (
    "获",
    "宣布",
    "发布",
    "推出",
    "进入",
    "回应",
    "跻身",
    "完成",
    "上线",
    "披露",
    "实现",
    "启动",
)
SECOND_HAND_CUES = (
    "据报道",
    "消息称",
    "传闻",
    "网传",
    "爆料",
    "编译",
    "转载",
    "转自",
    "整理自",
    "综合自",
    "rumor",
    "reportedly",
    "according to",
    "via ",
    "source:",
)
DEFAULT_PRIMARY_SOURCE_DOMAINS = (
    "openai.com",
    "anthropic.com",
    "deepseek.com",
    "deepmind.google",
    "mistral.ai",
    "cohere.com",
    "aliyun.com",
    "alibabacloud.com",
    "augmentcode.com",
    "blog.google",
    "ai.meta.com",
    "huggingface.co",
    "runwayml.com",
    "pika.art",
    "luma.ai",
    "lumalabs.ai",
    "stability.ai",
    "elevenlabs.io",
    "suno.com",
    "udio.com",
    "seed.bytedance.com",
    "bytedance.com",
    "tencent.com",
    "hunyuan.tencent.com",
    "moonshot.ai",
    "moonshot.cn",
    "bigmodel.cn",
    "z.ai",
    "minimax.io",
    "arxiv.org",
    "export.arxiv.org",
    "github.com",
)
DEFAULT_PRIMARY_X_HANDLES = (
    "sama",
    "openai",
    "anthropicai",
    "mistralai",
    "deepmind",
    "elonmusk",
    "demishassabis",
    "karpathy",
    "drjimfan",
    "tszzq",
    "goodfellow_ian",
    "codeeditapp",
    "replit",
    "runwayml",
    "elevenlabsio",
)
DEFAULT_SECOND_HAND_DOMAINS = (
    "qbitai.com",
    "36kr.com",
    "jiemian.com",
    "ifanr.com",
    "techcrunch.com",
    "theverge.com",
    "jiqizhixin.com",
    "zhidx.com",
)
X_HOSTS = {
    "x.com",
    "twitter.com",
    "nitter.net",
    "nitter.poast.org",
    "nitter.privacydev.net",
    "nitter.d420.de",
    "nitter.unixfox.eu",
}
REPORT_ITEM_TITLE_PATTERN = re.compile(r"^###\s+\d+\)\s+(.+)$")
REPORT_ITEM_SOURCE_PATTERN = re.compile(r"^- 来源[：:](.+)$")

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_time(entry: Any) -> Optional[datetime]:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            dt = dtparser.parse(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def normalize_host(host: str) -> str:
    normalized = host.strip().lower()
    if normalized.startswith("www."):
        normalized = normalized[4:]
    return normalized


def nitter_to_x_url(url: str) -> str:
    """将 Nitter 链接转为 x.com 原始链接，供读者直接访问。"""
    parsed = urlparse(url)
    host = normalize_host(parsed.netloc or "")
    if host not in X_HOSTS or host in {"x.com", "twitter.com"}:
        return url
    return parsed._replace(netloc="x.com").geturl()


def parse_csv_env(name: str, default_values: tuple[str, ...]) -> set[str]:
    raw = os.getenv(name)
    values = raw.split(",") if raw is not None else list(default_values)
    return {value.strip().lower() for value in values if value.strip()}


def host_matches(host: str, allowed_domains: set[str]) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


def extract_account_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return ""
    return path.split("/", 1)[0].strip().lower()


def contains_second_hand_cue(text: str) -> bool:
    normalized = text.lower()
    return any(cue in normalized for cue in SECOND_HAND_CUES)


def title_looks_incomplete(title: str) -> bool:
    candidate = clean_text(title)
    if len(candidate) < 4:
        return True
    return any(candidate.startswith(prefix) for prefix in TITLE_INCOMPLETE_PREFIXES)


def pick_preferred_title(candidate_title: str, fallback_title: str) -> str:
    candidate = clean_text(candidate_title)[:TITLE_MAX_CHARS]
    fallback = clean_text(fallback_title)[:TITLE_MAX_CHARS]
    if not candidate:
        return fallback
    if title_looks_incomplete(candidate) and fallback:
        return fallback
    return candidate


def key_point_dedupe_key(text: str) -> str:
    return re.sub(r"\W+", "", text.lower(), flags=re.UNICODE)


def normalize_key_point_text(text: str) -> str:
    value = clean_text(text)
    value = re.sub(r"^[\-*•·\d\.\)\(、\s]+", "", value)
    value = re.sub(r"^(并且|并将|并可|并支持|并|同时|且)\s*", "", value)
    value = value.strip("，,。；;：:、- ")
    return value[:KEY_POINT_MAX_CHARS]


def split_key_point_candidates(text: str) -> list[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []

    candidates: list[str] = []
    segments = re.split(r"[。！？!?；;]+", cleaned)
    for segment in segments:
        piece = segment.strip()
        if not piece:
            continue
        parts = [piece]
        if len(piece) > KEY_POINT_MAX_CHARS:
            parts = [part.strip() for part in re.split(r"[，,]|(?:\band\b)|(?:\bwith\b)", piece) if part.strip()]
        candidates.extend(parts)

    return candidates or [cleaned]


def normalize_key_points(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    points: list[str] = []
    seen: set[str] = set()
    for raw in value:
        for candidate in split_key_point_candidates(str(raw)):
            text = normalize_key_point_text(candidate)
            if len(text) < KEY_POINT_MIN_CHARS:
                continue
            key = key_point_dedupe_key(text)
            if not key or key in seen:
                continue
            seen.add(key)
            points.append(text)
            if len(points) >= KEY_POINTS_MAX_COUNT:
                return points
    return points


def build_default_key_points(item: dict[str, str]) -> list[str]:
    points: list[str] = []
    seen: set[str] = set()
    for field in ("summary", "brief", "impact", "title"):
        for candidate in split_key_point_candidates(item.get(field, "")):
            text = normalize_key_point_text(candidate)
            if len(text) < KEY_POINT_MIN_CHARS:
                continue
            key = key_point_dedupe_key(text)
            if not key or key in seen:
                continue
            seen.add(key)
            points.append(text)
            if len(points) >= KEY_POINTS_MAX_COUNT:
                return points

    if not points:
        fallback_text = normalize_key_point_text(item.get("title", "")) or "建议查看原文获取完整信息"
        points.append(fallback_text)

    return points[:KEY_POINTS_MAX_COUNT]


def ensure_sentence_end(text: str) -> str:
    value = clean_text(text)
    if not value:
        return ""
    if value[-1] in "。！？!?":
        return value
    return f"{value}。"


def shorten_for_highlight(text: str, max_chars: int = 42) -> str:
    value = clean_text(text)
    if len(value) <= max_chars:
        return value

    for sep in ("。", "；", ";", "，", ","):
        if sep in value:
            head = value.split(sep, 1)[0].strip()
            if 0 < len(head) <= max_chars:
                return head
    return value[:max_chars].rstrip()


def sentence_candidates(text: str) -> list[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    return [segment.strip() for segment in re.split(r"[。！？!?；;]+", cleaned) if segment.strip()]


def normalize_for_compare(text: str) -> str:
    return re.sub(r"\W+", "", clean_text(text).lower(), flags=re.UNICODE)


def extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", clean_text(text)))


def has_unseen_numbers(text: str, evidence: str) -> bool:
    numbers = extract_numbers(text)
    if not numbers:
        return False
    evidence_numbers = extract_numbers(evidence)
    return not numbers.issubset(evidence_numbers)


def fact_overlap_ratio(text: str, evidence: str) -> float:
    text_chars = {ch for ch in clean_text(text) if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff")}
    if not text_chars:
        return 0.0
    evidence_chars = {ch for ch in clean_text(evidence) if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff")}
    return len(text_chars & evidence_chars) / len(text_chars)


def extractive_brief(item: dict[str, str]) -> str:
    summary = clean_text(item.get("summary", ""))
    if not summary:
        return clean_text(item.get("title", ""))[:BRIEF_MAX_CHARS]
    sentences = sentence_candidates(summary)
    if sentences:
        return sentences[0][:BRIEF_MAX_CHARS]
    return summary[:BRIEF_MAX_CHARS]


def sanitize_item_factuality(item: dict[str, str]) -> dict[str, str]:
    if not STRICT_FACT_MODE:
        return item

    fixed = item.copy()
    evidence = f"{clean_text(fixed.get('title', ''))} {clean_text(fixed.get('summary', ''))}".strip()
    if not evidence:
        return fixed

    brief = clean_text(fixed.get("brief", ""))
    if (
        not brief
        or has_unseen_numbers(brief, evidence)
        or fact_overlap_ratio(brief, evidence) < FACT_OVERLAP_MIN
    ):
        brief = extractive_brief(fixed)
    fixed["brief"] = brief[:BRIEF_MAX_CHARS]

    details = clean_text(fixed.get("details", ""))
    if (
        not details
        or len(details) < DETAIL_MIN_CHARS
        or normalize_for_compare(details) == normalize_for_compare(brief)
        or has_unseen_numbers(details, evidence)
        or fact_overlap_ratio(details, evidence) < FACT_OVERLAP_MIN
    ):
        details = build_detail_from_summary(summary=fixed.get("summary", ""), brief=fixed.get("brief", ""))
    if not details:
        details = fixed["brief"]
    fixed["details"] = details[:DETAIL_MAX_CHARS]

    impact = clean_text(fixed.get("impact", ""))
    if impact and has_unseen_numbers(impact, evidence):
        fixed["impact"] = "该进展已在一手来源披露，建议结合原文评估实际影响。"

    return fixed


def sanitize_items_factuality(items: list[dict[str, str]]) -> list[dict[str, str]]:
    return [sanitize_item_factuality(item) for item in items]


def build_detail_from_summary(summary: str, brief: str) -> str:
    brief_key = normalize_for_compare(brief)
    detail_parts: list[str] = []
    for candidate in sentence_candidates(summary):
        if len(candidate) < 12:
            continue
        if normalize_for_compare(candidate) == brief_key:
            continue
        detail_parts.append(candidate)
        if len(detail_parts) >= 2:
            break
    if not detail_parts:
        return clean_text(summary)[:DETAIL_MAX_CHARS]
    detail_text = "；".join(detail_parts)
    return detail_text[:DETAIL_MAX_CHARS]


def fix_item_detail(item: dict[str, str]) -> dict[str, str]:
    fixed = item.copy()
    brief = clean_text(fixed.get("brief", ""))
    details = clean_text(fixed.get("details", ""))
    summary = clean_text(fixed.get("summary", ""))

    low_quality = (
        not details
        or len(details) < DETAIL_MIN_CHARS
        or normalize_for_compare(details) == normalize_for_compare(brief)
    )
    if low_quality and summary:
        details = build_detail_from_summary(summary=summary, brief=brief)
    if not details:
        details = brief
    fixed["details"] = details[:DETAIL_MAX_CHARS]
    return fixed


def fix_items_detail(items: list[dict[str, str]]) -> list[dict[str, str]]:
    return sanitize_items_factuality([fix_item_detail(item) for item in items])


def extract_urls(text: str) -> set[str]:
    matches = re.findall(r"https?://[^\s\]\)]+", text)
    return {match.rstrip(".,;:)]") for match in matches}


def extract_numeric_tokens(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", clean_text(text)))


def polish_result_is_safe(original_markdown: str, polished_markdown: str) -> bool:
    original_urls = extract_urls(original_markdown)
    polished_urls = extract_urls(polished_markdown)
    if original_urls != polished_urls:
        return False

    original_numbers = extract_numeric_tokens(original_markdown)
    polished_numbers = extract_numeric_tokens(polished_markdown)
    if not polished_numbers.issubset(original_numbers):
        return False

    return True


def finalize_key_points(points: list[str], item: dict[str, str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for text in points + build_default_key_points(item):
        normalized = normalize_key_point_text(text)
        if len(normalized) < KEY_POINT_MIN_CHARS:
            continue
        key = key_point_dedupe_key(normalized)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
        if len(merged) >= KEY_POINTS_MAX_COUNT:
            break

    if len(merged) < KEY_POINTS_MIN_COUNT:
        return build_default_key_points(item)
    return merged


def source_bucket_key(link: str) -> str:
    parsed = urlparse(link)
    host = normalize_host(parsed.netloc or "")
    if not host:
        return ""

    if host == "github.com":
        path_parts = [segment for segment in parsed.path.split("/") if segment]
        if len(path_parts) >= 2:
            return f"github:{path_parts[0].lower()}/{path_parts[1].lower()}"
        return host

    if host in X_HOSTS:
        account = extract_account_from_url(link)
        if account:
            return f"x:{account}"
        return "x:unknown"

    return host


def contains_second_hand_domain(text: str, blocked_domains: set[str]) -> bool:
    normalized = text.lower()
    return any(domain in normalized for domain in blocked_domains)


def parse_github_changelog_feed(source_url: str) -> tuple[str, str, str, str] | None:
    parsed = urlparse(source_url)
    host = normalize_host(parsed.netloc or "")
    if host != "github.com":
        return None

    path = parsed.path.strip("/")
    # e.g. owner/repo/commits/main/CHANGELOG.md.atom
    match = re.match(
        r"([^/]+)/([^/]+)/commits/([^/]+)/(.+)\.atom$",
        path,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    owner, repo, branch, tracked_file = match.groups()
    return owner, repo, branch, tracked_file


def normalize_link_for_source(source_url: str, link: str) -> str:
    feed_info = parse_github_changelog_feed(source_url)
    if not feed_info:
        return link

    owner, repo, branch, tracked_file = feed_info
    if tracked_file.lower().endswith("changelog.md"):
        return f"https://github.com/{owner}/{repo}/blob/{branch}/{tracked_file}"
    return link


def normalize_link_for_dedupe(url: str) -> str:
    parsed = urlparse((url or "").strip())
    host = normalize_host(parsed.netloc or "")
    if not host:
        return ""

    path = re.sub(r"/+$", "", parsed.path or "")
    if host in X_HOSTS:
        host = "x.com"
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 3 and parts[1] == "status":
            path = f"/{parts[0].lower()}/status/{parts[2]}"
        elif parts:
            path = f"/{parts[0].lower()}"
        else:
            path = ""
    elif host in {"arxiv.org", "export.arxiv.org"}:
        match = re.match(r"^/(abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?$", path, flags=re.IGNORECASE)
        if match:
            path = f"/{match.group(1).lower()}/{match.group(2)}"
        host = "arxiv.org"

    return f"{host}{path}".strip()


def normalize_title_for_dedupe(title: str) -> str:
    return re.sub(r"\W+", "", clean_text(title).lower(), flags=re.UNICODE)


def item_dedupe_fingerprints(item: dict[str, str]) -> set[str]:
    fingerprints: set[str] = set()
    link_key = normalize_link_for_dedupe(item.get("link", ""))
    if link_key:
        fingerprints.add(f"l:{link_key}")
    title_key = normalize_title_for_dedupe(item.get("title", ""))
    if title_key:
        fingerprints.add(f"t:{title_key}")
    return fingerprints


def collect_report_history_fingerprints(report_path: Path) -> set[str]:
    fingerprints: set[str] = set()
    current_title = ""
    try:
        lines = report_path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
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
        source = clean_text(source_match.group(1))
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
    except Exception as exc:
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
    items: list[dict[str, str]],
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
    items: list[dict[str, str]],
    history_fingerprints: set[str],
) -> tuple[list[dict[str, str]], int]:
    if not history_fingerprints:
        return items, 0

    kept: list[dict[str, str]] = []
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
    # e.g. owner/repo/commit/<sha>
    return bool(re.match(r"[^/]+/[^/]+/commit/[0-9a-f]{7,40}$", path, flags=re.IGNORECASE))


def get_primary_rejection_reason(
    item: dict[str, str],
    allowed_domains: set[str],
    allowed_x_handles: set[str],
    blocked_domains: set[str] | None = None,
) -> str | None:
    link = (item.get("link", "") or "").strip()
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

    evidence = f"{clean_text(item.get('title', ''))} {clean_text(item.get('summary', ''))}".strip()
    if evidence and contains_second_hand_cue(evidence):
        return "second_hand_cue"

    if blocked_domains is None:
        blocked_domains = parse_csv_env("SECOND_HAND_DOMAINS", DEFAULT_SECOND_HAND_DOMAINS)
    if evidence and contains_second_hand_domain(evidence, blocked_domains):
        return "second_hand_domain"

    return None


def is_primary_item(
    item: dict[str, str],
    allowed_domains: set[str],
    allowed_x_handles: set[str],
) -> bool:
    return get_primary_rejection_reason(
        item=item,
        allowed_domains=allowed_domains,
        allowed_x_handles=allowed_x_handles,
    ) is None


def filter_primary_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    filtered, _ = filter_primary_items_with_stats(items)
    return filtered


def filter_primary_items_with_stats(items: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
    strict_primary_only = os.getenv("STRICT_PRIMARY_ONLY", "1").strip().lower()
    if strict_primary_only in {"0", "false", "no", "off"}:
        return items, {"strict_mode_disabled": len(items)}

    allowed_domains = parse_csv_env("PRIMARY_SOURCE_DOMAINS", DEFAULT_PRIMARY_SOURCE_DOMAINS)
    allowed_x_handles = parse_csv_env("PRIMARY_X_HANDLES", DEFAULT_PRIMARY_X_HANDLES)
    blocked_domains = parse_csv_env("SECOND_HAND_DOMAINS", DEFAULT_SECOND_HAND_DOMAINS)
    filtered: list[dict[str, str]] = []
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


def apply_source_limits(items: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
    per_domain_limit = int_env("PER_DOMAIN_LIMIT", 4, min_value=0, max_value=50)
    arxiv_max_items = int_env("ARXIV_MAX_ITEMS", 4, min_value=0, max_value=50)

    if per_domain_limit <= 0 and arxiv_max_items <= 0:
        return items, {}

    kept: list[dict[str, str]] = []
    bucket_counts: dict[str, int] = {}
    arxiv_count = 0
    dropped: dict[str, int] = {}

    for item in items:
        link = item.get("link", "")
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


def load_sources(path: str = "sources.txt") -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    raw_sources = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    expanded: list[str] = []
    for source in raw_sources:
        expanded.extend(expand_source_urls(source))
    return list(dict.fromkeys(expanded))


_nitter_alive_cache: list[str] | None = None


def probe_nitter_bases(bases: list[str], timeout: float = 5.0) -> list[str]:
    """探测哪些 Nitter 实例可用，返回存活列表（结果缓存）。"""
    global _nitter_alive_cache
    if _nitter_alive_cache is not None:
        return _nitter_alive_cache

    from urllib import request as urlrequest, error as urlerror

    alive: list[str] = []
    for base in bases:
        try:
            req = urlrequest.Request(f"{base}/", method="HEAD")
            with urlrequest.urlopen(req, timeout=timeout):
                alive.append(base)
        except Exception:
            logger.warning("nitter instance down: %s", base)
    if not alive:
        logger.error("all nitter instances are down, X/Twitter sources will be unavailable")
    else:
        logger.info("nitter alive instances: %d/%d", len(alive), len(bases))
    _nitter_alive_cache = alive
    return alive


def expand_source_urls(source: str) -> list[str]:
    parsed = urlparse(source)
    host = (parsed.netloc or "").lower()

    if host in {"github.com", "www.github.com"}:
        path = (parsed.path or "").strip("/")
        # Support direct changelog URL:
        # https://github.com/<owner>/<repo>/blob/<branch>/CHANGELOG.md
        match = re.match(
            r"([^/]+)/([^/]+)/blob/([^/]+)/(.+)$",
            path,
            flags=re.IGNORECASE,
        )
        if match:
            owner, repo, branch, tracked_file = match.groups()
            if tracked_file.lower().endswith("changelog.md"):
                return [f"https://github.com/{owner}/{repo}/commits/{branch}/{tracked_file}.atom"]

    if host in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        path = (parsed.path or "").strip("/")
        handle = path.split("/", 1)[0] if path else ""
        reserved = {"home", "explore", "search", "i", "messages", "notifications", "settings"}
        if handle and handle not in reserved:
            raw_bases = os.getenv(
                "NITTER_RSS_BASES",
                "https://nitter.net,https://nitter.poast.org,https://nitter.privacydev.net",
            )
            all_bases = [base.strip().rstrip("/") for base in raw_bases.split(",") if base.strip()]
            bases = probe_nitter_bases(list(dict.fromkeys(all_bases)))
            if not bases:
                logger.warning("skipping X source (no alive nitter): %s", source)
                return []
            return [f"{base}/{handle}/rss" for base in bases]

    return [source]


def _fetch_single_source(
    source: str, cutoff: datetime, per_source: int,
) -> tuple[str, list[dict[str, str]], str | None]:
    """抓取单个 RSS 源，返回 (source_url, items, error_reason)。"""
    try:
        feed = feedparser.parse(source)
    except Exception as exc:
        return source, [], str(exc)

    entries = getattr(feed, "entries", [])
    if getattr(feed, "bozo", 0) and not entries:
        return source, [], str(getattr(feed, "bozo_exception", "bozo"))
    if not entries:
        return source, [], None

    parsed_items: list[dict[str, str]] = []
    for entry in entries[:per_source]:
        title = clean_text(entry.get("title", ""))
        raw_link = (entry.get("link", "") or "").split("#")[0]
        link = normalize_link_for_source(source_url=source, link=raw_link)
        summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
        published = parse_time(entry)

        if not title or not link:
            continue
        if published and published < cutoff:
            continue

        parsed_items.append(
            {
                "title": title[:200],
                "link": link,
                "summary": summary[:1000],
                "published": published.isoformat() if published else "",
            }
        )
    return source, parsed_items, None


def fetch_items(
    sources: list[str], hours: int = 36, per_source: int = 30, max_workers: int = 10,
) -> list[dict[str, str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    source_stats: dict[str, int] = {"success": 0, "empty": 0, "error": 0}
    failed_sources: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_single_source, src, cutoff, per_source): src
            for src in sources
        }
        for future in as_completed(futures, timeout=180):
            source, source_items, error = future.result()
            if error:
                source_stats["error"] += 1
                failed_sources.append(source)
                logger.warning("source fetch failed: %s (reason=%s)", source, error)
                continue
            if not source_items:
                source_stats["empty"] += 1
                continue

            source_stats["success"] += 1
            for parsed in source_items:
                key = hashlib.md5(
                    (parsed["link"].split("?")[0] + "|" + parsed["title"].lower()).encode("utf-8")
                ).hexdigest()
                if key in seen:
                    continue
                seen.add(key)
                items.append(parsed)

    logger.info(
        "source fetch stats: success=%s empty=%s error=%s total=%s",
        source_stats["success"], source_stats["empty"], source_stats["error"], len(sources),
    )
    if failed_sources:
        logger.warning("failed sources (%d): %s", len(failed_sources), ", ".join(failed_sources[:10]))

    items.sort(key=lambda x: x.get("published", ""), reverse=True)
    return items


def llm_chat(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int | None = None,
) -> str:
    params: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    if max_tokens is not None and max_tokens > 0:
        params["max_tokens"] = max_tokens

    response = client.chat.completions.create(**params)
    return (response.choices[0].message.content or "").strip()


def extract_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    candidates: list[str] = [raw]

    if raw.startswith("```"):
        fence_stripped = re.sub(r"^```(?:json)?", "", raw).strip()
        fence_stripped = re.sub(r"```$", "", fence_stripped).strip()
        candidates.append(fence_stripped)

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(raw[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("model output is not valid JSON object")


def fallback_selection(items: list[dict[str, str]], top_n: int, start_score: int = 100) -> list[dict[str, str]]:
    fallback: list[dict[str, str]] = []
    for idx, item in enumerate(items[:top_n], 1):
        result = item.copy()
        result["score"] = str(max(start_score - idx + 1, 0))

        summary = clean_text(item.get("summary", ""))
        if summary:
            result["brief"] = summary[:BRIEF_MAX_CHARS]
        else:
            result["brief"] = clean_text(item.get("title", ""))[:BRIEF_MAX_CHARS]

        result["details"] = summary[:DETAIL_MAX_CHARS] if summary else result["brief"]
        result["impact"] = "信息持续跟进中，建议查看原文链接。"
        result["key_points"] = build_default_key_points(result)
        fallback.append(result)
    return fallback


def backfill_selected_items(
    selected: list[dict[str, str]],
    items: list[dict[str, str]],
    top_n: int,
) -> list[dict[str, str]]:
    target_count = min(top_n, len(items))
    if len(selected) >= target_count:
        return selected[:target_count]

    used_fingerprints: set[str] = set()
    for item in selected:
        used_fingerprints.update(item_dedupe_fingerprints(item))

    remaining: list[dict[str, str]] = []
    for item in items:
        fingerprints = item_dedupe_fingerprints(item)
        if fingerprints and used_fingerprints.intersection(fingerprints):
            continue
        used_fingerprints.update(fingerprints)
        remaining.append(item)

    needed = target_count - len(selected)
    if needed <= 0:
        return selected[:target_count]

    last_score = 100
    if selected:
        try:
            last_score = int(selected[-1].get("score", "100"))
        except (TypeError, ValueError):
            last_score = 100

    selected.extend(fallback_selection(remaining, top_n=needed, start_score=max(last_score - 1, 0)))
    return selected[:target_count]


def rank_and_summarize(
    items: list[dict[str, str]],
    qwen_api_key: str,
    qwen_model: str,
    top_n: int = 20,
) -> list[dict[str, str]]:
    client = OpenAI(api_key=qwen_api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

    candidates: list[str] = []
    for idx, item in enumerate(items, 1):
        candidates.append(
            (
                f"{idx}. 标题: {item['title']}\n"
                f"链接: {item['link']}\n"
                f"内容: {item['summary'][:350]}\n"
                f"发布时间: {item['published']}\n"
            )
        )

    user_prompt = (
        "你是AI资讯编辑。请从候选中选出最值得做早报的内容并摘要。\n"
        "严格输出JSON："
        '{"items":[{"id":1,"score":90,"title":"...","brief":"...","details":"...","impact":"...","key_points":["...","..."]}]}\n'
        f"最多返回{top_n}条；title<={TITLE_MAX_CHARS}字；brief<={BRIEF_MAX_CHARS}字；details<={DETAIL_MAX_CHARS}字；impact<={IMPACT_MAX_CHARS}字；必须基于输入，不编造；"
        "brief和impact必须使用简体中文。"
        "details写1-2句具体事实，尽量包含实体名/数字/版本/时间等可核实信息。"
        f"key_points返回2-3条，每条<={KEY_POINT_MAX_CHARS}字。"
        "标题必须完整，包含主体名称（公司/产品/人物），不能省略主语。"
        "写法要可直接用于朋友圈/公众号：先结论后细节、避免空话与套话。"
        "brief只写1句，尽量包含“主体+动作+结果”；impact回答“为什么值得关注”。"
        "仅可选择一手来源（官方公告、论文原文、作者/机构本人账号原帖），"
        "禁止媒体转述、二手解读、汇总搬运、未证实传闻。\n\n"
        + "\n".join(candidates)
    )

    last_error: Exception | None = None
    data: dict[str, Any] | None = None
    for attempt in range(2):
        system_prompt = "你是严谨的科技新闻编辑，只输出JSON。"
        if attempt > 0:
            system_prompt = (
                "你是严谨的科技新闻编辑。"
                "你上一次输出格式错误，这次必须仅输出一个合法JSON对象，不要输出任何说明文字。"
            )

        raw = llm_chat(
            client=client,
            model=qwen_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        try:
            data = extract_json(raw)
            break
        except ValueError as exc:
            last_error = exc

    if data is None:
        logger.warning("rank_and_summarize: 模型输出无法解析，使用 fallback。error=%s", last_error)
        return fallback_selection(items=items, top_n=top_n)

    selected: list[dict[str, str]] = []
    used_item_ids: set[int] = set()
    selected_fingerprints: set[str] = set()
    rows = data.get("items", [])
    if not isinstance(rows, list):
        logger.warning("rank_and_summarize: items 字段不是列表，使用 fallback。")
        return fallback_selection(items=items, top_n=top_n)

    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            idx = int(row.get("id", 0))
        except (TypeError, ValueError):
            continue
        if idx < 1 or idx > len(items):
            continue
        if idx in used_item_ids:
            continue
        result = items[idx - 1].copy()
        try:
            score = int(row.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        result["score"] = str(score)
        title = pick_preferred_title(str(row.get("title", "")), result.get("title", ""))
        if title:
            if title != clean_text(str(row.get("title", "")))[:TITLE_MAX_CHARS]:
                logger.info("rank_and_summarize: 标题疑似缺主语，回退为原始标题。")
            result["title"] = title
        result["brief"] = clean_text(str(row.get("brief", "")))[:BRIEF_MAX_CHARS]
        details = clean_text(str(row.get("details", "")))[:DETAIL_MAX_CHARS]
        if not details:
            details = clean_text(result.get("summary", ""))[:DETAIL_MAX_CHARS]
        if not details:
            details = result["brief"]
        result["details"] = details
        result["impact"] = clean_text(str(row.get("impact", "")))[:IMPACT_MAX_CHARS]
        result["key_points"] = finalize_key_points(normalize_key_points(row.get("key_points")), result)
        fingerprints = item_dedupe_fingerprints(result)
        if fingerprints and selected_fingerprints.intersection(fingerprints):
            continue
        selected_fingerprints.update(fingerprints)
        used_item_ids.add(idx)
        selected.append(result)

    selected.sort(key=lambda x: int(x.get("score", "0")), reverse=True)
    if not selected:
        logger.warning("rank_and_summarize: 解析结果为空，使用 fallback。")
        return fallback_selection(items=items, top_n=top_n)
    selected = backfill_selected_items(selected=selected, items=items, top_n=top_n)
    selected.sort(key=lambda x: int(x.get("score", "0")), reverse=True)
    selected = selected[: min(top_n, len(items))]
    return fix_items_detail(selected)


def localize_items_to_chinese(
    items: list[dict[str, str]],
    qwen_api_key: str,
    qwen_model: str,
) -> list[dict[str, str]]:
    if not items:
        return items

    client = OpenAI(api_key=qwen_api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    payload = [
        {
            "id": idx + 1,
            "title": item.get("title", ""),
            "brief": item.get("brief", ""),
            "details": item.get("details", ""),
            "impact": item.get("impact", ""),
            "key_points": item.get("key_points", [])[:KEY_POINTS_MAX_COUNT],
        }
        for idx, item in enumerate(items)
    ]

    user_prompt = (
        "请把下面资讯字段统一改写为简体中文，必须保持事实不变。\n"
        "严格输出JSON："
        '{"items":[{"id":1,"title":"中文标题","brief":"中文摘要","details":"中文细节","impact":"中文影响","key_points":["要点1","要点2"]}]}\n'
        f"要求：title<={TITLE_MAX_CHARS}字，brief<={BRIEF_MAX_CHARS}字，details<={DETAIL_MAX_CHARS}字，impact<={IMPACT_MAX_CHARS}字，"
        f"key_points最多{KEY_POINTS_MAX_COUNT}条且每条<={KEY_POINT_MAX_CHARS}字。\n\n"
        "文风要求：口语化但专业，信息密度高，像可直接发朋友圈/公众号的成稿。"
        "避免机械重复开头（如连续使用“宣布/发布”）。\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    try:
        raw = llm_chat(
            client=client,
            model=qwen_model,
            system_prompt="你是中文科技编辑，只输出合法JSON。",
            user_prompt=user_prompt,
        )
        data = extract_json(raw)
    except Exception as exc:
        logger.warning("localize_items_to_chinese: 本地化失败，回退原文。error=%s", exc)
        return items

    rows = data.get("items", [])
    if not isinstance(rows, list):
        return items

    id_to_row: dict[int, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            idx = int(row.get("id", 0))
        except (TypeError, ValueError):
            continue
        if 1 <= idx <= len(items):
            id_to_row[idx] = row

    localized: list[dict[str, str]] = []
    for idx, item in enumerate(items, 1):
        row = id_to_row.get(idx)
        if row is None:
            localized.append(item)
            continue

        merged = item.copy()
        title_cn = clean_text(str(row.get("title", "")))[:TITLE_MAX_CHARS]
        brief_cn = clean_text(str(row.get("brief", "")))[:BRIEF_MAX_CHARS]
        details_cn = clean_text(str(row.get("details", "")))[:DETAIL_MAX_CHARS]
        impact_cn = clean_text(str(row.get("impact", "")))[:IMPACT_MAX_CHARS]

        if title_cn:
            merged["title"] = title_cn
        if brief_cn:
            merged["brief"] = brief_cn
        if details_cn:
            merged["details"] = details_cn
        if impact_cn:
            merged["impact"] = impact_cn
        merged["key_points"] = finalize_key_points(normalize_key_points(row.get("key_points")), merged)
        localized.append(merged)

    missed = len(items) - len(id_to_row)
    if missed > 0:
        logger.warning("localize_items_to_chinese: %d/%d 条未被本地化，保留原文。", missed, len(items))
    return fix_items_detail(localized)


def polish_with_kimi(markdown: str, kimi_api_key: str, kimi_model: str) -> str:
    if not kimi_api_key:
        return markdown

    client = OpenAI(api_key=kimi_api_key, base_url="https://api.moonshot.cn/v1")
    prompt = (
        "请润色以下AI早报Markdown："
        "1) 不改事实和链接；2) 保持简洁专业；3) 不新增未提供的信息；"
        "4) 文风适合直接发朋友圈/公众号，减少机器感。\n\n"
        + markdown
    )
    try:
        polished = llm_chat(
            client=client,
            model=kimi_model,
            system_prompt="你是中文科技编辑。",
            user_prompt=prompt,
        )
    except Exception as exc:
        logger.warning("polish_with_kimi: 润色失败，回退原稿。error=%s", exc)
        return markdown

    if not polish_result_is_safe(markdown, polished):
        logger.warning("polish_with_kimi: 检测到潜在事实漂移，回退原稿。")
        return markdown

    return polished


SOURCE_CATEGORY_DOMAINS: dict[str, set[str]] = {
    "vendor": {
        "openai.com", "anthropic.com", "deepseek.com", "deepmind.google", "mistral.ai",
        "cohere.com", "ai.meta.com", "stability.ai", "runwayml.com", "elevenlabs.io",
        "suno.com", "pika.art", "luma.ai", "lumalabs.ai", "udio.com",
        "seed.bytedance.com", "bytedance.com", "tencent.com", "hunyuan.tencent.com",
        "moonshot.ai", "moonshot.cn", "bigmodel.cn", "minimax.io",
        "aliyun.com", "alibabacloud.com", "augmentcode.com",
    },
    "academic": {"arxiv.org", "export.arxiv.org"},
    "social": X_HOSTS,
    "github": {"github.com"},
}


def check_category_balance(items: list[dict[str, str]]) -> dict[str, int]:
    """统计各类来源分布并输出告警。"""
    counts: dict[str, int] = {cat: 0 for cat in SOURCE_CATEGORY_DOMAINS}
    counts["other"] = 0
    for item in items:
        host = normalize_host(urlparse(item.get("link", "")).netloc or "")
        matched = False
        for cat, domains in SOURCE_CATEGORY_DOMAINS.items():
            if host_matches(host, domains):
                counts[cat] += 1
                matched = True
                break
        if not matched:
            counts["other"] += 1

    logger.info("category balance: %s", json.dumps(counts, ensure_ascii=False))
    total = len(items)
    if total > 0:
        for cat, count in counts.items():
            if count / total >= 0.7 and total >= 5:
                logger.warning(
                    "category '%s' dominates report (%d/%d = %.0f%%), content diversity may be low",
                    cat, count, total, count / total * 100,
                )
    if counts.get("vendor", 0) == 0 and total > 0:
        logger.warning("no vendor news in final report, consider checking source availability")
    return counts


def render_markdown(items: list[dict[str, str]]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# AI 早报（{today}）",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 30秒导读",
    ]

    for idx, item in enumerate(items[:5], 1):
        title = clean_text(item.get("title", ""))
        brief = shorten_for_highlight(item.get("brief", ""))
        if title and brief:
            lines.append(f"- {idx}. {title}：{ensure_sentence_end(brief)}")
        elif brief:
            lines.append(f"- {idx}. {ensure_sentence_end(brief)}")
        else:
            lines.append(f"- {idx}. {title}")

    lines.append("")
    lines.append("## 详细快讯")
    for idx, item in enumerate(items, 1):
        brief = ensure_sentence_end(item.get("brief", ""))
        details = ensure_sentence_end(item.get("details", "") or item.get("brief", ""))
        impact = ensure_sentence_end(item.get("impact", ""))
        lines.extend(
            [
                "",
                f"### {idx}) {item['title']}",
                f"- 摘要：{brief}",
                f"- 细节：{details}",
                "- 关键点：",
                *[f"  - {point}" for point in finalize_key_points(normalize_key_points(item.get("key_points")), item)],
                f"- 影响：{impact}",
                f"- 来源：{nitter_to_x_url(item['link'])}",
                "---",
            ]
        )
    if lines and lines[-1] == "---":
        lines.pop()
    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    qwen_api_key = os.getenv("QWEN_API_KEY", "").strip()
    if not qwen_api_key:
        raise RuntimeError("QWEN_API_KEY 未设置")

    qwen_model = os.getenv("QWEN_MODEL", "qwen-flash")
    kimi_api_key = os.getenv("KIMI_API_KEY", "").strip()
    kimi_model = os.getenv("KIMI_MODEL", "kimi-latest")
    max_items = int_env("MAX_ITEMS", 120, min_value=10, max_value=500)
    top_n = int_env("TOP_N", 20, min_value=5, max_value=100)
    fetch_hours = int_env("FETCH_HOURS", 24, min_value=1, max_value=168)
    fallback_fetch_hours = int_env("FALLBACK_FETCH_HOURS", 72, min_value=1, max_value=168)
    per_source_items = int_env("PER_SOURCE_ITEMS", 30, min_value=5, max_value=200)
    history_dedupe_days = int_env("HISTORY_DEDUP_DAYS", 2, min_value=0, max_value=30)
    history_state_max_days = int_env("HISTORY_STATE_MAX_DAYS", 14, min_value=1, max_value=90)

    report_dir = Path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    history_state_path = Path(os.getenv("HISTORY_STATE_PATH", str(report_dir / "history_index.json")))
    history_state = load_history_state(history_state_path)
    history_fingerprints = load_recent_history_fingerprints(report_dir=report_dir, lookback_days=history_dedupe_days)
    history_fingerprints.update(history_state_fingerprints(history_state, lookback_days=history_dedupe_days))

    sources = load_sources("sources.txt")
    fetched_items = fetch_items(sources=sources, hours=fetch_hours, per_source=per_source_items)

    def prepare_items(
        raw_items: list[dict[str, str]],
    ) -> tuple[list[dict[str, str]], dict[str, int], dict[str, int], int]:
        filtered_items, rejected_stats = filter_primary_items_with_stats(raw_items)
        diversified_items, diversity_stats = apply_source_limits(filtered_items)
        history_filtered_items, history_dropped = filter_items_by_history(diversified_items, history_fingerprints)
        return history_filtered_items[:max_items], rejected_stats, diversity_stats, history_dropped

    items, rejected_stats, diversity_stats, history_dropped = prepare_items(fetched_items)

    if len(items) < top_n and fallback_fetch_hours > fetch_hours:
        expanded_fetched_items = fetch_items(
            sources=sources,
            hours=fallback_fetch_hours,
            per_source=per_source_items,
        )
        if len(expanded_fetched_items) > len(fetched_items):
            items, rejected_stats, diversity_stats, history_dropped = prepare_items(expanded_fetched_items)
            fetched_items = expanded_fetched_items

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
    if diversity_stats:
        logger.info("source limit dropped reasons=%s", json.dumps(diversity_stats, ensure_ascii=False))
    if not items:
        raise RuntimeError("未抓到一手资讯，请检查 sources.txt 或放宽 STRICT_PRIMARY_ONLY 配置")

    selected = rank_and_summarize(items=items, qwen_api_key=qwen_api_key, qwen_model=qwen_model, top_n=top_n)
    selected = localize_items_to_chinese(items=selected, qwen_api_key=qwen_api_key, qwen_model=qwen_model)
    check_category_balance(selected)
    markdown = render_markdown(selected)
    markdown = polish_with_kimi(markdown=markdown, kimi_api_key=kimi_api_key, kimi_model=kimi_model)

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

    print(f"done: {daily}")


if __name__ == "__main__":
    main()
