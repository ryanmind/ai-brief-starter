#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import (  # noqa: E402
    DEFAULT_PRIMARY_SOURCE_DOMAINS,
    DEFAULT_PRIMARY_X_HANDLES,
    DEFAULT_SECOND_HAND_DOMAINS,
    DETAIL_WEAK_PHRASES,
    TITLE_INCOMPLETE_PREFIXES,
    X_HOSTS,
    float_env,
    parse_csv_env,
)

SUMMARY_LINE_PATTERN = re.compile(
    r"^(?P<prefix>\s*(?:[-*]\s*)?(?:\*{0,2})?(?:摘要|summary)(?:\*{0,2})?\s*[：:]\s*)(?P<value>.*)$",
    flags=re.IGNORECASE,
)
DETAIL_LINE_PATTERN = re.compile(
    r"^(?P<prefix>\s*(?:[-*]\s*)?(?:\*{0,2})?(?:细节|详情|detail)(?:\*{0,2})?\s*[：:]\s*)(?P<value>.*)$",
    flags=re.IGNORECASE,
)
IMPACT_PATTERN = re.compile(
    r"^(?:[-*]\s*)?(?:\*{0,2})?(?:影响分析|影响|impact)(?:\*{0,2})?\s*[：:]\s*(.+)$",
    flags=re.IGNORECASE,
)
SOURCE_PATTERN = re.compile(
    r"^(?:[-*]\s*)?(?:\*{0,2})?(?:来源|source)(?:\*{0,2})?\s*[：:]\s*(.+)$",
    flags=re.IGNORECASE,
)
TITLE_PATTERN = re.compile(r"^###\s*\d+[)\.、]\s*(.+)$")
TITLE_VERSION_ONLY_PATTERN = re.compile(
    r"^(?:v?\d+(?:\.\d+){1,3})(?:\s*(?:版本|版|release|update|上线))?$",
    flags=re.IGNORECASE,
)
KEY_POINTS_HEADER_PATTERN = re.compile(r"^(?:[-*]\s*)?(?:\*{0,2})?关键点(?:\*{0,2})?\s*[：:]?$")
BULLET_PATTERN = re.compile(r"^\s*(?:[-*•]\s+|\d+\.\s+)(.+)$")
SUMMARY_HEADER_PATTERN = re.compile(r"^(?:\*{0,2})?(?:摘要|summary)(?:\*{0,2})?\s*[：:]?$", flags=re.IGNORECASE)
DETAIL_HEADER_PATTERN = re.compile(r"^(?:\*{0,2})?(?:细节|详情|detail)(?:\*{0,2})?\s*[：:]?$", flags=re.IGNORECASE)
IMPACT_HEADER_PATTERN = re.compile(
    r"^(?:\*{0,2})?(?:影响分析|影响|impact)(?:\*{0,2})?\s*[：:]?$",
    flags=re.IGNORECASE,
)
SOURCE_HEADER_PATTERN = re.compile(r"^(?:\*{0,2})?(?:来源|source)(?:\*{0,2})?\s*[：:]?$", flags=re.IGNORECASE)
MARKDOWN_LINK_URL_PATTERN = re.compile(r"\[[^\]]+\]\((https?://[^)\s]+)\)")
PLAIN_URL_PATTERN = re.compile(r"https?://[^\s\]\)]+")


@dataclass
class Evaluation:
    metrics: dict[str, object]
    errors: list[str]
    warnings: list[str]
    high_risk_items: list[dict[str, str]]


def is_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def extract_first_url(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    md_match = MARKDOWN_LINK_URL_PATTERN.search(text)
    if md_match:
        return md_match.group(1).strip()
    plain_match = PLAIN_URL_PATTERN.search(text)
    if plain_match:
        return plain_match.group(0).strip().rstrip(".,;:)]")
    return ""


def normalize_host(url: str) -> str:
    parsed_source = extract_first_url(url) or url
    host = (urlparse(parsed_source).netloc or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def host_matches(host: str, domains: set[str]) -> bool:
    return any(host == d or host.endswith(f".{d}") for d in domains)


def extract_account_from_url(url: str) -> str:
    parsed_source = extract_first_url(url) or url
    path = urlparse(parsed_source).path.strip("/")
    if not path:
        return ""
    return path.split("/", 1)[0].strip().lower()


def title_looks_incomplete(title: str) -> bool:
    clean_title = re.sub(r"\s+", " ", title.strip())
    if len(clean_title) < 4:
        return True
    lowered = clean_title.lower()
    if any(lowered.startswith(prefix.lower()) for prefix in TITLE_INCOMPLETE_PREFIXES):
        return True
    if TITLE_VERSION_ONLY_PATTERN.match(clean_title):
        return True
    if re.match(r"^v?\d+(?:\.\d+){1,3}\b", clean_title, flags=re.IGNORECASE):
        return True
    if lowered.startswith(("release:", "chore:", "fix:", "feat:", "docs:", "ci:", "build:")):
        return True
    return False


def normalize_for_compare(text: str) -> str:
    return re.sub(r"\W+", "", text.strip().lower(), flags=re.UNICODE)


def split_key_point_candidates(text: str) -> list[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []

    chunks: list[str] = []
    for sentence in re.split(r"[。！？!?；;]+", cleaned):
        sentence = sentence.strip()
        if not sentence:
            continue
        parts = [sentence]
        if len(sentence) > 28:
            parts = [part.strip() for part in re.split(r"[，,]", sentence) if part.strip()]
        chunks.extend(parts)
    return chunks


def normalize_key_point_text(text: str, max_chars: int) -> str:
    value = clean_text(text)
    value = re.sub(r"^[\-*•·\d\.\)\(、\s]+", "", value)
    value = re.sub(r"^(并且|并将|并可|并支持|并|同时|且)\s*", "", value)
    value = value.strip("，,。；;：:、- ")
    return value[:max_chars]


def build_key_points_from_fields(
    summary: str,
    detail: str,
    title: str,
    existing: list[str],
    min_count: int,
    max_count: int,
    max_chars: int,
) -> list[str]:
    points: list[str] = []
    seen: set[str] = set()

    for raw in existing + split_key_point_candidates(summary) + split_key_point_candidates(detail) + [title]:
        normalized = normalize_key_point_text(str(raw), max_chars=max_chars)
        if len(normalized) < 4:
            continue
        key = normalize_for_compare(normalized)
        if not key or key in seen:
            continue
        seen.add(key)
        points.append(normalized)
        if len(points) >= max_count:
            break

    if not points:
        points = [normalize_key_point_text(title, max_chars=max_chars) or "建议查看来源了解完整信息"]

    while len(points) < min_count:
        candidate = normalize_key_point_text(summary or detail or title, max_chars=max_chars)
        if not candidate or normalize_for_compare(candidate) in seen:
            break
        seen.add(normalize_for_compare(candidate))
        points.append(candidate)

    return points[:max_count]


def build_detail_from_existing_fields(
    title: str,
    summary: str,
    detail: str,
    key_points: list[str],
    min_chars: int,
) -> str:
    pieces: list[str] = []
    seen: set[str] = set()

    def add_piece(raw: str) -> None:
        value = re.sub(r"\s+", " ", str(raw).strip())
        if not value:
            return
        normalized = normalize_for_compare(value)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        pieces.append(value.strip("，,。；; "))

    add_piece(summary)
    for point in key_points:
        add_piece(point)
        if len("；".join(pieces)) >= min_chars:
            break

    add_piece(detail)
    if not pieces:
        add_piece(title)

    merged = "；".join(piece for piece in pieces if piece)
    if not merged:
        merged = "该进展已在一手来源披露并持续更新"
    if normalize_for_compare(merged) == normalize_for_compare(summary):
        merged = f"{merged}；当前条目基于一手来源原文整理"
    filler = "当前条目基于一手来源原文整理，建议结合来源链接查看完整上下文"
    while len(merged) < min_chars:
        merged = f"{merged}；{filler}"
    if merged and merged[-1] not in "。！？!?":
        merged += "。"
    return merged


def build_summary_from_existing_fields(title: str, detail: str, key_points: list[str], max_chars: int = 56) -> str:
    for raw in key_points + split_key_point_candidates(detail) + [detail, title]:
        value = clean_text(str(raw))
        if not value:
            continue
        value = re.sub(r"^[\-*•·\d\.\)\(、\s]+", "", value).strip("，,。；;：:- ")
        if len(value) >= 4:
            return value[:max_chars]
    fallback = clean_text(title) or "该进展已披露，建议结合来源查看完整信息"
    return fallback[:max_chars]


def parse_report_structure(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    items: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_key_points = False
    pending_field: str | None = None

    for idx, line in enumerate(lines):
        stripped = line.strip()
        title_match = TITLE_PATTERN.match(stripped)
        if title_match:
            if current is not None:
                current["end_idx"] = idx
                items.append(current)
            current = {
                "title": title_match.group(1).strip(),
                "title_idx": idx,
                "end_idx": len(lines),
                "summary": "",
                "summary_idx": None,
                "summary_prefix": "**摘要**：",
                "detail": "",
                "detail_idx": None,
                "detail_prefix": "**细节**：",
                "impact": "",
                "impact_idx": None,
                "impact_prefix": "**影响分析**：",
                "source": "",
                "source_idx": None,
                "source_prefix": "**来源**：",
                "key_points": [],
                "key_points_header_idx": None,
                "key_point_line_indices": [],
            }
            in_key_points = False
            pending_field = None
            continue

        if current is None:
            continue

        summary_match = SUMMARY_LINE_PATTERN.match(line)
        if summary_match:
            current["summary_prefix"] = summary_match.group("prefix")
            current["summary"] = summary_match.group("value").strip()
            current["summary_idx"] = idx
            if not current["summary"]:
                pending_field = "summary"
            in_key_points = False
            if current["summary"]:
                pending_field = None
            continue

        detail_match = DETAIL_LINE_PATTERN.match(line)
        if detail_match:
            current["detail_prefix"] = detail_match.group("prefix")
            current["detail"] = detail_match.group("value").strip()
            current["detail_idx"] = idx
            if not current["detail"]:
                pending_field = "detail"
            in_key_points = False
            if current["detail"]:
                pending_field = None
            continue

        impact_match = IMPACT_PATTERN.match(stripped)
        if impact_match:
            current["impact"] = impact_match.group(1).strip()
            current["impact_idx"] = idx
            current["impact_prefix"] = stripped.split("：", 1)[0].split(":", 1)[0] + "："
            in_key_points = False
            pending_field = None
            continue

        source_match = SOURCE_PATTERN.match(stripped)
        if source_match:
            source_value = source_match.group(1).strip()
            current["source"] = extract_first_url(source_value) or source_value
            current["source_idx"] = idx
            current["source_prefix"] = stripped.split("：", 1)[0].split(":", 1)[0] + "："
            in_key_points = False
            if not current["source"]:
                pending_field = "source"
            else:
                pending_field = None
            continue

        if KEY_POINTS_HEADER_PATTERN.match(stripped):
            in_key_points = True
            pending_field = None
            current["key_points_header_idx"] = idx
            continue

        if SUMMARY_HEADER_PATTERN.match(stripped):
            in_key_points = False
            pending_field = "summary"
            continue

        if DETAIL_HEADER_PATTERN.match(stripped):
            in_key_points = False
            pending_field = "detail"
            continue

        if IMPACT_HEADER_PATTERN.match(stripped):
            in_key_points = False
            pending_field = "impact"
            continue

        if SOURCE_HEADER_PATTERN.match(stripped):
            in_key_points = False
            pending_field = "source"
            continue

        if in_key_points:
            bullet_match = BULLET_PATTERN.match(line)
            if bullet_match:
                point = bullet_match.group(1).strip()
                if point:
                    key_points = current["key_points"]
                    if isinstance(key_points, list):
                        key_points.append(point)
                    line_indices = current["key_point_line_indices"]
                    if isinstance(line_indices, list):
                        line_indices.append(idx)
                continue
            if stripped and stripped != "---":
                in_key_points = False

        if pending_field and stripped and stripped != "---":
            value = stripped
            if pending_field == "source":
                value = extract_first_url(value) or value
            current[pending_field] = value
            current[f"{pending_field}_idx"] = idx
            pending_field = None

    if current is not None:
        current["end_idx"] = len(lines)
        items.append(current)

    return items


def extract_report_items(text: str) -> list[dict[str, object]]:
    items = parse_report_structure(text)
    cleaned: list[dict[str, object]] = []
    for item in items:
        cleaned.append(
            {
                "title": str(item.get("title", "")),
                "summary": str(item.get("summary", "")),
                "detail": str(item.get("detail", "")),
                "impact": str(item.get("impact", "")),
                "source": str(item.get("source", "")),
                "key_points": item.get("key_points", []),
            }
        )
    return cleaned


def autofix_report(path: Path, key_points_min_count: int, key_points_max_count: int, key_point_max_chars: int) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        return 0

    items = parse_report_structure(text)
    edits: list[tuple[int, int, list[str]]] = []

    for item in items:
        title = str(item.get("title", "")).strip()
        summary = str(item.get("summary", "")).strip()
        detail = str(item.get("detail", "")).strip()
        title_idx = item.get("title_idx")
        summary_idx = item.get("summary_idx")
        summary_prefix = str(item.get("summary_prefix", "**摘要**："))
        key_points_raw = item.get("key_points", [])
        key_points = [str(point).strip() for point in key_points_raw] if isinstance(key_points_raw, list) else []

        # Summary autofix
        if not summary:
            new_summary = build_summary_from_existing_fields(
                title=title,
                detail=detail,
                key_points=key_points,
            )
            if isinstance(summary_idx, int):
                edits.append((summary_idx, summary_idx + 1, [f"{summary_prefix}{new_summary}"]))
            else:
                insert_at = title_idx + 1 if isinstance(title_idx, int) else 0
                edits.append((insert_at, insert_at, [f"**摘要**：{new_summary}"]))
                summary_idx = insert_at
                summary_prefix = "**摘要**："
            summary = new_summary

        # Key points autofix
        too_long_points = [point for point in key_points if len(point) > key_point_max_chars]
        key_point_issue = (
            len(key_points) < key_points_min_count
            or len(key_points) > key_points_max_count
            or bool(too_long_points)
        )
        if key_point_issue:
            new_points = build_key_points_from_fields(
                summary=summary,
                detail=detail,
                title=title,
                existing=key_points,
                min_count=key_points_min_count,
                max_count=key_points_max_count,
                max_chars=key_point_max_chars,
            )

            header_idx = item.get("key_points_header_idx")
            if isinstance(header_idx, int):
                point_indices = item.get("key_point_line_indices", [])
                start = header_idx + 1
                end = start
                if isinstance(point_indices, list) and point_indices:
                    start = min(point_indices)
                    end = max(point_indices) + 1
                edits.append((start, end, [f"- {point}" for point in new_points]))
            else:
                impact_idx = item.get("impact_idx")
                source_idx = item.get("source_idx")
                detail_idx = item.get("detail_idx")
                insert_at = title_idx + 1 if isinstance(title_idx, int) else 0
                if isinstance(summary_idx, int):
                    insert_at = summary_idx + 1
                if isinstance(detail_idx, int):
                    insert_at = detail_idx + 1
                if isinstance(source_idx, int):
                    insert_at = source_idx
                if isinstance(impact_idx, int):
                    insert_at = impact_idx
                block = ["**关键点**"] + [f"- {point}" for point in new_points]
                edits.append((insert_at, insert_at, block))

    if not edits:
        return 0

    # Apply from bottom to top so line offsets remain valid.
    for start, end, new_lines in sorted(edits, key=lambda x: x[0], reverse=True):
        lines[start:end] = new_lines

    new_text = "\n".join(lines)
    if text.endswith("\n"):
        new_text += "\n"
    path.write_text(new_text, encoding="utf-8")
    return len(edits)


def is_primary_source(source: str, allowed_domains: set[str], allowed_x_handles: set[str]) -> bool:
    host = normalize_host(source)
    if not host:
        return False
    if host in X_HOSTS:
        account = extract_account_from_url(source)
        if not account:
            return False
        if allowed_x_handles and account not in allowed_x_handles:
            return False
        return True
    return host_matches(host, allowed_domains)


def source_category(source: str) -> str:
    host = normalize_host(source)
    if not host:
        return "other"
    if host in {"arxiv.org", "export.arxiv.org"}:
        return "academic"
    if host == "github.com":
        return "github"
    if host in X_HOSTS:
        return "social"
    if host_matches(host, {
        "openai.com", "anthropic.com", "deepseek.com", "deepmind.google", "mistral.ai", "cohere.com",
        "ai.meta.com", "stability.ai", "runwayml.com", "elevenlabs.io", "suno.com", "pika.art", "luma.ai",
        "lumalabs.ai", "udio.com", "seed.bytedance.com", "bytedance.com", "tencent.com", "hunyuan.tencent.com",
        "moonshot.ai", "moonshot.cn", "bigmodel.cn", "minimax.io", "aliyun.com", "alibabacloud.com",
        "augmentcode.com", "huggingface.co",
    }):
        return "vendor"
    return "other"


def detect_high_risk_items(items: list[dict[str, object]]) -> list[dict[str, str]]:
    finance_cues = {"融资", "估值", "亿美元", "万元", "轮融资", "ipo", "revenue", "arr", "营收"}
    policy_cues = {"政策", "监管", "法案", "禁令", "合规", "government", "eu", "白宫", "许可证"}

    risky: list[dict[str, str]] = []
    for idx, item in enumerate(items, 1):
        title = clean_text(str(item.get("title", "")))
        source = clean_text(str(item.get("source", "")))
        text = " ".join(
            [
                title,
                clean_text(str(item.get("summary", ""))),
                clean_text(str(item.get("detail", ""))),
                clean_text(str(item.get("impact", ""))),
            ]
        ).lower()
        numbers = re.findall(r"\d+(?:\.\d+)?%?", text)

        reasons: list[str] = []
        if any(cue in text for cue in finance_cues):
            reasons.append("融资/财务信息")
        if any(cue in text for cue in policy_cues):
            reasons.append("政策/监管信息")
        if len(numbers) >= 4:
            reasons.append("数字密集")

        if reasons:
            risky.append(
                {
                    "id": str(idx),
                    "title": title,
                    "source": source,
                    "reason": "、".join(dict.fromkeys(reasons)),
                }
            )

    return risky


def write_high_risk_report(path: Path, high_risk_items: list[dict[str, str]]) -> None:
    lines = ["# 高风险条目清单", "", "发布前建议人工快速复核以下条目（约 1 分钟）。", ""]
    if not high_risk_items:
        lines.append("- 本次未识别到高风险条目。")
    else:
        for item in high_risk_items:
            lines.append(f"- {item['id']}) {item['title']}（原因：{item['reason']}）")
            if item.get("source"):
                lines.append(f"  - 来源：{item['source']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate_report(path: Path, strict_mode: bool) -> Evaluation:
    text = path.read_text(encoding="utf-8")
    items = extract_report_items(text)
    titles = [str(item.get("title", "")) for item in items]

    title_complete_ratio_min = float_env("TITLE_COMPLETE_RATIO_MIN", 0.90, min_value=0.5, max_value=1.0)
    primary_source_ratio_min = float_env("PRIMARY_SOURCE_RATIO_MIN", 0.85, min_value=0.0, max_value=1.0)
    key_points_min_count = int(os.getenv("KEY_POINTS_MIN_COUNT", "2"))
    key_points_max_count = int(os.getenv("KEY_POINTS_MAX_COUNT", "3"))
    key_point_max_chars = int(os.getenv("KEY_POINT_MAX_CHARS", "28"))
    detail_min_chars = int(os.getenv("DETAIL_MIN_CHARS", "48"))

    blocked_domains = parse_csv_env("SECOND_HAND_DOMAINS", DEFAULT_SECOND_HAND_DOMAINS)
    allowed_domains = parse_csv_env("PRIMARY_SOURCE_DOMAINS", DEFAULT_PRIMARY_SOURCE_DOMAINS)
    allowed_x_handles = parse_csv_env("PRIMARY_X_HANDLES", DEFAULT_PRIMARY_X_HANDLES)

    errors: list[str] = []
    warnings: list[str] = []
    failure_reasons: dict[str, int] = {}

    def add_failure(code: str, message: str, as_error: bool = True) -> None:
        failure_reasons[code] = failure_reasons.get(code, 0) + 1
        if as_error:
            errors.append(message)
        else:
            warnings.append(message)

    if not titles:
        add_failure("no_items", "no report items found", as_error=True)

    incomplete_count = sum(1 for title in titles if title_looks_incomplete(title))
    complete_ratio = (len(titles) - incomplete_count) / len(titles) if titles else 0.0
    if complete_ratio < title_complete_ratio_min:
        add_failure(
            "title_incomplete_ratio",
            f"title complete ratio {complete_ratio:.2f} < threshold {title_complete_ratio_min:.2f}",
            as_error=strict_mode,
        )

    blocked_hits: list[str] = []
    missing_source_issues: list[str] = []
    structure_issues: list[str] = []
    optional_detail_issues: list[str] = []
    key_point_issues: list[str] = []
    missing_impact_issues: list[str] = []

    category_counts: dict[str, int] = {"vendor": 0, "academic": 0, "social": 0, "github": 0, "other": 0}
    primary_source_count = 0
    source_count = 0

    for idx, item in enumerate(items, 1):
        title = clean_text(str(item.get("title", "")))
        summary = clean_text(str(item.get("summary", "")))
        detail = clean_text(str(item.get("detail", "")))
        source = clean_text(str(item.get("source", "")))
        impact = clean_text(str(item.get("impact", "")))

        if not summary:
            structure_issues.append(f"{idx}) {title}: 缺少摘要字段")
        if not source:
            missing_source_issues.append(f"{idx}) {title}: 缺少来源链接")
        elif not normalize_host(source):
            missing_source_issues.append(f"{idx}) {title}: 来源链接无效")
        else:
            source_count += 1
            category_counts[source_category(source)] += 1
            if is_primary_source(source, allowed_domains, allowed_x_handles):
                primary_source_count += 1
            if host_matches(normalize_host(source), blocked_domains):
                blocked_hits.append(source)

        if detail:
            if len(detail) < detail_min_chars:
                optional_detail_issues.append(f"{idx}) {title}: 细节过短(len={len(detail)})")
            if summary and normalize_for_compare(summary) == normalize_for_compare(detail):
                optional_detail_issues.append(f"{idx}) {title}: 细节与摘要重复")
            if any(phrase in detail for phrase in DETAIL_WEAK_PHRASES):
                optional_detail_issues.append(f"{idx}) {title}: 细节内容过泛")

        points = item.get("key_points", [])
        if not isinstance(points, list):
            key_point_issues.append(f"{idx}) {title}: key_points字段不是列表")
        else:
            if len(points) < key_points_min_count or len(points) > key_points_max_count:
                key_point_issues.append(f"{idx}) {title}: 关键点数量={len(points)}")
            too_long = [point for point in points if len(clean_text(str(point))) > key_point_max_chars]
            if too_long:
                key_point_issues.append(f"{idx}) {title}: 存在超长关键点({len(too_long)}条)")

        if not impact:
            missing_impact_issues.append(f"{idx}) {title}: 影响字段为空")

    primary_source_ratio = (primary_source_count / source_count) if source_count else 0.0
    if missing_source_issues:
        add_failure("missing_source", "missing source links found", as_error=True)
    if structure_issues:
        add_failure("structure_missing", "template required fields missing", as_error=True)
    if blocked_hits:
        add_failure("blocked_source", "blocked second-hand domains found", as_error=strict_mode)
    if primary_source_ratio < primary_source_ratio_min:
        add_failure(
            "primary_ratio",
            f"primary source ratio {primary_source_ratio:.2f} < threshold {primary_source_ratio_min:.2f}",
            as_error=True,
        )
    if key_point_issues:
        add_failure("key_points", "key point format issues found", as_error=strict_mode)

    # P2 warnings: only warn, never block.
    total = len(items)
    if total >= 5:
        dominant_category, dominant_count = max(category_counts.items(), key=lambda x: x[1])
        if dominant_count / total >= 0.7:
            warnings.append(f"category imbalance warning: {dominant_category}={dominant_count}/{total}")

    detail_values = [clean_text(str(item.get("detail", ""))) for item in items if clean_text(str(item.get("detail", "")))]
    avg_detail_len = 0.0
    if detail_values:
        avg_detail_len = sum(len(value) for value in detail_values) / len(detail_values)
        if avg_detail_len < detail_min_chars + 8:
            warnings.append(f"legacy detail warning: average detail length is low ({avg_detail_len:.1f})")

    if missing_impact_issues:
        warnings.append(f"non-core field warning: missing impact on {len(missing_impact_issues)} item(s)")

    high_risk_items = detect_high_risk_items(items)

    metrics: dict[str, object] = {
        "total_items": len(items),
        "title_complete_ratio": round(complete_ratio, 4),
        "primary_source_ratio": round(primary_source_ratio, 4),
        "blocked_sources": len(blocked_hits),
        "missing_source_issues": len(missing_source_issues),
        "structure_issues": len(structure_issues),
        "optional_detail_issues": len(optional_detail_issues),
        "key_point_issues": len(key_point_issues),
        "warning_count": len(warnings),
        "missing_impact_count": len(missing_impact_issues),
        "legacy_avg_detail_len": round(avg_detail_len, 2),
        "high_risk_count": len(high_risk_items),
        "category_counts": category_counts,
        "failure_reasons": dict(sorted(failure_reasons.items(), key=lambda item: item[1], reverse=True)),
    }

    # Print a concise summary to logs.
    print(
        "quality summary:",
        f"items={metrics['total_items']}",
        f"title_complete_ratio={metrics['title_complete_ratio']}",
        f"primary_source_ratio={metrics['primary_source_ratio']}",
        f"optional_detail_issues={metrics['optional_detail_issues']}",
        f"key_point_issues={metrics['key_point_issues']}",
        f"warnings={metrics['warning_count']}",
    )

    if missing_source_issues:
        print("ERROR: missing source issues found:")
        for issue in missing_source_issues:
            print(f"- {issue}")

    if structure_issues:
        print("ERROR: structure issues found:")
        for issue in structure_issues:
            print(f"- {issue}")

    if blocked_hits:
        level = "ERROR" if strict_mode else "WARN"
        print(f"{level}: blocked second-hand domains found:")
        for hit in blocked_hits:
            print(f"- {hit}")

    if key_point_issues:
        level = "ERROR" if strict_mode else "WARN"
        print(f"{level}: key point format issues found:")
        for issue in key_point_issues:
            print(f"- {issue}")

    if optional_detail_issues:
        print("WARN: optional detail quality issues found:")
        for issue in optional_detail_issues:
            print(f"- {issue}")

    for warning in warnings:
        print(f"WARN: {warning}")

    return Evaluation(metrics=metrics, errors=errors, warnings=warnings, high_risk_items=high_risk_items)


def run_checks(
    path: Path,
    autofix: bool = False,
    metrics_output: Path | None = None,
    high_risk_output: Path | None = None,
) -> int:
    if not path.exists():
        print(f"ERROR: report not found: {path}")
        return 1

    strict_mode = is_enabled(os.getenv("QUALITY_CHECK_STRICT"), default=True)
    key_points_min_count = int(os.getenv("KEY_POINTS_MIN_COUNT", "2"))
    key_points_max_count = int(os.getenv("KEY_POINTS_MAX_COUNT", "3"))
    key_point_max_chars = int(os.getenv("KEY_POINT_MAX_CHARS", "28"))

    repaired_count = 0
    if autofix:
        repaired_count = autofix_report(
            path,
            key_points_min_count=key_points_min_count,
            key_points_max_count=key_points_max_count,
            key_point_max_chars=key_point_max_chars,
        )
        if repaired_count > 0:
            print(f"info: autofix repaired {repaired_count} field block(s)")

    evaluation = evaluate_report(path, strict_mode=strict_mode)
    evaluation.metrics["repaired_count"] = repaired_count
    evaluation.metrics["strict_mode"] = strict_mode
    evaluation.metrics["passed"] = (not evaluation.errors) or not strict_mode

    if metrics_output is not None:
        metrics_output.parent.mkdir(parents=True, exist_ok=True)
        metrics_output.write_text(
            json.dumps(evaluation.metrics, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if high_risk_output is not None:
        write_high_risk_report(high_risk_output, evaluation.high_risk_items)

    if strict_mode and evaluation.errors:
        return 1

    if not strict_mode and evaluation.errors:
        print("info: quality check running in soft mode (QUALITY_CHECK_STRICT=0), continue without failing")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate report quality.")
    parser.add_argument("report", nargs="?", default="reports/latest.md")
    parser.add_argument("--autofix", action="store_true", help="Auto-repair summary/key point fields before checks")
    parser.add_argument("--metrics-output", default="", help="Optional JSON output path for quality metrics")
    parser.add_argument("--high-risk-output", default="", help="Optional markdown output path for high-risk items")
    args = parser.parse_args()

    metrics_output = Path(args.metrics_output) if args.metrics_output else None
    high_risk_output = Path(args.high_risk_output) if args.high_risk_output else None
    return run_checks(
        path=Path(args.report),
        autofix=args.autofix,
        metrics_output=metrics_output,
        high_risk_output=high_risk_output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
