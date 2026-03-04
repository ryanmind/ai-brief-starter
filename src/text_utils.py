"""Shared text processing utilities.

All text cleaning, normalization, key-point processing, and fact-check
helpers live here so they can be reused by main, scripts, and tests.
"""
from __future__ import annotations

import re
from typing import Any, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse

from dateutil import parser as dtparser

from src.config import (
    BRIEF_MAX_CHARS,
    DETAIL_MAX_CHARS,
    DETAIL_MIN_CHARS,
    FACT_OVERLAP_MIN,
    KEY_POINT_MAX_CHARS,
    KEY_POINT_MIN_CHARS,
    KEY_POINTS_MAX_COUNT,
    KEY_POINTS_MIN_COUNT,
    SECOND_HAND_CUES,
    STRICT_FACT_MODE,
    TITLE_INCOMPLETE_PREFIXES,
    TITLE_MAX_CHARS,
    X_HOSTS,
    IMPACT_MAX_CHARS,
)


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
        except (TypeError, ValueError, OverflowError):
            continue

    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = entry.get(key)
        if not value:
            continue
        try:
            return datetime(*value[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError, OverflowError):
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


MARKDOWN_LINK_URL_PATTERN = re.compile(r"\[[^\]]+\]\((https?://[^\)\s]+)\)")
PLAIN_URL_PATTERN = re.compile(r"https?://[^\s\]\)]+")


def extract_first_url(text: str) -> str:
    content = str(text or "").strip()
    if not content:
        return ""
    md_link_match = MARKDOWN_LINK_URL_PATTERN.search(content)
    if md_link_match:
        return md_link_match.group(1).strip()
    plain_match = PLAIN_URL_PATTERN.search(content)
    if plain_match:
        return plain_match.group(0).strip().rstrip(".,;:)]")
    return ""


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
    lowered = candidate.lower()
    return any(lowered.startswith(prefix.lower()) for prefix in TITLE_INCOMPLETE_PREFIXES)


VERSION_TOKEN_PATTERN = re.compile(r"\bv?\d+(?:\.\d+){1,3}\b", flags=re.IGNORECASE)
TITLE_VERSION_ONLY_PATTERN = re.compile(
    r"^(?:v?\d+(?:\.\d+){1,3})(?:\s*(?:版本|版|release|update|上线))?$",
    flags=re.IGNORECASE,
)


def extract_source_subject(link: str) -> str:
    parsed = urlparse(link)
    host = normalize_host(parsed.netloc or "")
    if not host:
        return ""
    if host == "github.com":
        parts = [segment for segment in parsed.path.split("/") if segment]
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
    if host in X_HOSTS:
        account = extract_account_from_url(link)
        if account:
            return f"@{account}"
    return host


def title_needs_subject_context(title: str) -> bool:
    candidate = clean_text(title)
    if title_looks_incomplete(candidate):
        return True
    if TITLE_VERSION_ONLY_PATTERN.match(candidate):
        return True
    if re.match(r"^v?\d+(?:\.\d+){1,3}\b", candidate, flags=re.IGNORECASE):
        return True
    lowered = candidate.lower()
    if lowered.startswith(("release:", "chore:", "fix:", "feat:", "docs:", "ci:", "build:")):
        return True
    return False


def build_contextual_title(title: str, summary: str, link: str) -> str:
    candidate = clean_text(title)[:TITLE_MAX_CHARS]
    if not candidate:
        return candidate
    if not title_needs_subject_context(candidate):
        return candidate

    subject = extract_source_subject(link)
    combined = f"{candidate} {clean_text(summary)}"
    version_match = VERSION_TOKEN_PATTERN.search(combined)
    version = version_match.group(0) if version_match else ""

    if subject and version:
        return f"{subject} 发布 {version} 版本更新"[:TITLE_MAX_CHARS]
    if subject:
        return f"{subject} 发布产品更新"[:TITLE_MAX_CHARS]
    if version:
        return f"发布 {version} 版本更新"[:TITLE_MAX_CHARS]
    return candidate


def pick_preferred_title(candidate_title: str, fallback_title: str) -> str:
    candidate = clean_text(candidate_title)[:TITLE_MAX_CHARS]
    fallback = clean_text(fallback_title)[:TITLE_MAX_CHARS]
    if not candidate:
        return fallback
    if title_looks_incomplete(candidate) and fallback:
        return fallback
    return candidate


SUBJECT_ACTION_MARKERS = (
    "发布",
    "推出",
    "宣布",
    "上线",
    "更新",
    "开源",
    "达成",
    "回应",
    "披露",
)


def title_has_explicit_subject(title: str) -> bool:
    candidate = clean_text(title)
    if not candidate:
        return False
    if candidate.startswith("@"):
        return True
    if re.match(r"^[^/\s]{2,40}/[^/\s]{2,60}\s+", candidate):
        return True

    lowered = candidate.lower()
    if re.match(r"^[a-z][\w@./-]{1,40}\s+(?:releases?|launches?|announces?|updates?)\b", lowered):
        return True

    for marker in SUBJECT_ACTION_MARKERS:
        pos = candidate.find(marker)
        if pos <= 0:
            continue
        subject = clean_text(candidate[:pos]).strip("：:：- ")
        if not subject:
            continue
        if TITLE_VERSION_ONLY_PATTERN.match(subject):
            continue
        if re.match(
            r"^v?\d+(?:\.\d+){1,3}(?:\s*(?:版本|版))?(?:\s*(?:即将|将|预计|或|soon|coming))?$",
            subject,
            flags=re.IGNORECASE,
        ):
            continue
        if re.match(r"^v?\d+(?:\.\d+){1,3}$", subject, flags=re.IGNORECASE):
            continue
        return True
    return False


def build_subject_guaranteed_title(title: str, summary: str, link: str) -> str:
    candidate = build_contextual_title(title=title, summary=summary, link=link)
    if candidate and title_has_explicit_subject(candidate):
        return candidate

    subject = extract_source_subject(link)
    combined = f"{clean_text(title)} {clean_text(summary)}"
    version_match = VERSION_TOKEN_PATTERN.search(combined)
    version = version_match.group(0) if version_match else ""

    if subject and version:
        return f"{subject} 发布 {version} 版本更新"[:TITLE_MAX_CHARS]
    if subject:
        return f"{subject} 发布重要更新"[:TITLE_MAX_CHARS]
    if version:
        return f"相关项目发布 {version} 版本更新"[:TITLE_MAX_CHARS]
    return clean_text(title)[:TITLE_MAX_CHARS] or "相关项目发布重要更新"


def key_point_dedupe_key(text: str) -> str:
    return re.sub(r"\W+", "", text.lower(), flags=re.UNICODE)


def normalize_key_point_text(text: str) -> str:
    value = clean_text(text)
    value = re.sub(r"^[\-*•·\d\.\)\(、\s]+", "", value)
    value = re.sub(r"^(?:关键点|要点)\s*[：:]\s*", "", value)
    value = re.sub(r"^(并且|并将|并可|并支持|并|同时|且)\s*", "", value)
    value = value.strip("，,。；;：:、- ")
    if is_placeholder_text(value):
        return ""
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


LOW_SIGNAL_TERMS: tuple[str, ...] = (
    "人工智能",
    "大模型",
    "生成式模型",
    "智能体",
    "图像",
    "视频",
    "音频",
    "接口",
    "开发工具包",
)
LOW_SIGNAL_CLAUSE_PATTERN = re.compile(
    r"^(?:" + "|".join(re.escape(term) for term in LOW_SIGNAL_TERMS) + r")+$"
)
PLACEHOLDER_TEXT_PATTERN = re.compile(
    r"^(?:value|null|none|n/?a|na|unknown|待补充|暂无|无)$",
    flags=re.IGNORECASE,
)


def collapse_duplicate_punctuation(text: str) -> str:
    value = text
    value = re.sub(r"[，,]{2,}", "，", value)
    value = re.sub(r"[；;]{2,}", "；", value)
    value = re.sub(r"[：:]{2,}", "：", value)
    value = re.sub(r"([，,；;：:])(?:\s*[，,；;：:])+", r"\1", value)
    return value


def is_placeholder_text(text: str) -> bool:
    value = clean_text(text).strip(" ，,。；;：:-_—")
    if not value:
        return True
    return bool(PLACEHOLDER_TEXT_PATTERN.fullmatch(value))


def sanitize_generated_clause(text: str) -> str:
    clause = clean_text(text)
    if not clause:
        return ""
    if is_placeholder_text(clause):
        return ""
    clause = re.sub(r"(?<!\w)@+(?!\w)", " ", clause)
    clause = re.sub(r"['''\"""]+", "", clause)
    clause = re.sub(r"[（）()\[\]【】{}<>《》]+", "", clause)
    clause = re.sub(r"\s*[-—–]+\s*", "-", clause)
    clause = collapse_duplicate_punctuation(clause)
    clause = clause.strip(" ，,。；;：:、-—–")
    compact = re.sub(r"[，,。；;：:、\-—–\s\.!?！？…·]", "", clause)
    if not compact:
        return ""
    if re.fullmatch(r"\d+(?:\.\d+)?", compact):
        return ""
    if LOW_SIGNAL_CLAUSE_PATTERN.fullmatch(compact):
        return ""
    return clause


def clean_generated_text(text: str) -> str:
    value = clean_text(text)
    if not value:
        return ""

    value = collapse_duplicate_punctuation(value)
    clauses = re.split(r"[；;]+", value)
    cleaned_clauses: list[str] = []
    seen: set[str] = set()
    for clause in clauses:
        cleaned = sanitize_generated_clause(clause)
        if not cleaned:
            continue
        key = key_point_dedupe_key(cleaned)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        cleaned_clauses.append(cleaned)

    if cleaned_clauses:
        value = "；".join(cleaned_clauses)
    else:
        value = sanitize_generated_clause(value)

    value = collapse_duplicate_punctuation(value)
    value = re.sub(r"\s*([，,；;：:])\s*", r"\1", value)
    value = re.sub(r"([，,；;：:])[。！？!?]+", r"\1", value)
    return value.strip(" ，,。；;：:-")


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
    matches = PLAIN_URL_PATTERN.findall(text)
    return {match.rstrip(".,;:)]") for match in matches}


def extract_numeric_tokens(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", clean_text(text)))


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


def contains_second_hand_domain(text: str, blocked_domains: set[str]) -> bool:
    normalized = text.lower()
    return any(domain in normalized for domain in blocked_domains)


def build_fallback_impact(item: dict[str, str]) -> str:
    brief = clean_text(item.get("brief", ""))
    summary = clean_text(item.get("summary", ""))
    title = clean_text(item.get("title", ""))
    brief_key = normalize_for_compare(brief)

    for candidate in sentence_candidates(summary):
        normalized = normalize_for_compare(candidate)
        if not normalized or normalized == brief_key:
            continue
        if len(candidate) < 12:
            continue
        return candidate[:IMPACT_MAX_CHARS]

    if title:
        return f"{title}相关进展已由一手来源披露，预计将影响后续产品与行业节奏。"[:IMPACT_MAX_CHARS]
    if brief:
        return f"{brief[:28]}这一进展已披露，预计将影响相关技术与应用落地节奏。"[:IMPACT_MAX_CHARS]
    return "该进展已由一手来源披露，预计将影响相关技术与产业节奏。"


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
    dedupe_link = item.get("dedupe_link", "") or item.get("link", "")
    link_key = normalize_link_for_dedupe(dedupe_link)
    if link_key:
        fingerprints.add(f"l:{link_key}")
    title_key = normalize_title_for_dedupe(item.get("title", ""))
    if title_key:
        fingerprints.add(f"t:{title_key}")
    return fingerprints


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


def strip_markdown_fence(text: str) -> str:
    value = str(text or "").strip()
    if not value.startswith("```"):
        return value
    value = re.sub(r"^```(?:markdown|md)?\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*```$", "", value)
    return value.strip()


def polish_result_is_safe(original_markdown: str, polished_markdown: str) -> bool:
    original_urls = extract_urls(original_markdown)
    polished_urls = extract_urls(polished_markdown)
    if original_urls != polished_urls:
        return False

    original_numbers = extract_numeric_tokens(original_markdown)
    polished_numbers = extract_numeric_tokens(polished_markdown)
    if not polished_numbers.issubset(original_numbers):
        return False

    # Keep report structure stable after polishing.
    structure_patterns = (
        re.compile(r"(?m)^###\s*\d+[)\.、]\s+"),
        re.compile(r"(?m)^(?:-\s*)?(?:\*{0,2})?(?:摘要|summary)(?:\*{0,2})\s*[：:]"),
        re.compile(r"(?m)^(?:-\s*)?(?:\*{0,2})?(?:细节|详情|detail)(?:\*{0,2})\s*[：:]"),
        re.compile(r"(?m)^(?:-\s*)?(?:\*{0,2})?关键点(?:\*{0,2})\s*[：:]?$"),
        re.compile(r"(?m)^(?:-\s*)?(?:\*{0,2})?(?:影响分析|影响|impact)(?:\*{0,2})\s*[：:]"),
        re.compile(r"(?m)^(?:-\s*)?(?:\*{0,2})?(?:来源|source)(?:\*{0,2})\s*[：:]"),
    )
    for pattern in structure_patterns:
        if len(pattern.findall(original_markdown)) != len(pattern.findall(polished_markdown)):
            return False

    return True
