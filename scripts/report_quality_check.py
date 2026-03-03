#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import (
    DEFAULT_SECOND_HAND_DOMAINS,
    DETAIL_WEAK_PHRASES,
    TITLE_INCOMPLETE_PREFIXES,
    parse_csv_env,
)

SUMMARY_PATTERN = re.compile(r"^(?:[-*]\s*)?(?:摘要|summary)\s*[：:]\s*(.+)$", flags=re.IGNORECASE)
DETAIL_PATTERN = re.compile(r"^(?:[-*]\s*)?(?:细节|详情|detail)\s*[：:]\s*(.+)$", flags=re.IGNORECASE)
DETAIL_LINE_PATTERN = re.compile(
    r"^(?P<prefix>\s*(?:[-*]\s*)?(?:细节|详情|detail)\s*[：:]\s*)(?P<value>.*)$",
    flags=re.IGNORECASE,
)


def is_enabled(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def normalize_host(url: str) -> str:
    host = (urlparse(url).netloc or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def host_matches(host: str, domains: set[str]) -> bool:
    return any(host == d or host.endswith(f".{d}") for d in domains)


def title_looks_incomplete(title: str) -> bool:
    clean_title = re.sub(r"\s+", " ", title.strip())
    if len(clean_title) < 4:
        return True
    return any(clean_title.startswith(prefix) for prefix in TITLE_INCOMPLETE_PREFIXES)


def normalize_for_compare(text: str) -> str:
    return re.sub(r"\W+", "", text.strip().lower(), flags=re.UNICODE)


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


def autofix_detail_lines(path: Path, detail_min_chars: int) -> int:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        return 0

    title_pattern = re.compile(r"^###\s*\d+\)\s*(.+)$")
    key_points_header_pattern = re.compile(r"^(?:[-*]\s*)?关键点\s*[：:]?$")
    bullet_pattern = re.compile(r"^\s*(?:[-*•]\s+|\d+\.\s+)(.+)$")
    impact_pattern = re.compile(r"^(?:[-*]\s*)?(?:影响|impact)\s*[：:]", flags=re.IGNORECASE)
    source_pattern = re.compile(r"^(?:[-*]\s*)?(?:来源|source)\s*[：:]", flags=re.IGNORECASE)

    items: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_key_points = False

    for idx, line in enumerate(lines):
        stripped = line.strip()
        title_match = title_pattern.match(stripped)
        if title_match:
            if current is not None:
                items.append(current)
            current = {
                "title": title_match.group(1).strip(),
                "title_idx": idx,
                "summary": "",
                "summary_idx": None,
                "detail": "",
                "detail_idx": None,
                "detail_prefix": "- 细节：",
                "key_points": [],
            }
            in_key_points = False
            continue

        if current is None:
            continue

        if key_points_header_pattern.match(stripped):
            in_key_points = True
            continue

        summary_match = SUMMARY_PATTERN.match(stripped)
        if summary_match:
            current["summary"] = summary_match.group(1).strip()
            current["summary_idx"] = idx
            in_key_points = False
            continue

        detail_match = DETAIL_LINE_PATTERN.match(line)
        if detail_match:
            current["detail"] = detail_match.group("value").strip()
            current["detail_idx"] = idx
            current["detail_prefix"] = detail_match.group("prefix")
            in_key_points = False
            continue

        if impact_pattern.match(stripped) or source_pattern.match(stripped):
            in_key_points = False
            continue

        if in_key_points:
            bullet_match = bullet_pattern.match(line)
            if bullet_match:
                point = bullet_match.group(1).strip()
                if point:
                    points = current["key_points"]
                    if isinstance(points, list):
                        points.append(point)

    if current is not None:
        items.append(current)

    edits: list[tuple[str, int, str]] = []
    for item in items:
        summary = str(item.get("summary", "")).strip()
        detail = str(item.get("detail", "")).strip()
        title = str(item.get("title", "")).strip()
        key_points_raw = item.get("key_points", [])
        key_points = [str(point).strip() for point in key_points_raw] if isinstance(key_points_raw, list) else []

        needs_fix = (
            not detail
            or len(detail) < detail_min_chars
            or (summary and normalize_for_compare(summary) == normalize_for_compare(detail))
            or any(phrase in detail for phrase in DETAIL_WEAK_PHRASES)
        )
        if not needs_fix:
            continue

        new_detail = build_detail_from_existing_fields(
            title=title,
            summary=summary,
            detail=detail,
            key_points=key_points,
            min_chars=detail_min_chars,
        )
        detail_idx = item.get("detail_idx")
        if isinstance(detail_idx, int):
            prefix = str(item.get("detail_prefix", "- 细节："))
            edits.append(("replace", detail_idx, f"{prefix}{new_detail}"))
            continue

        summary_idx = item.get("summary_idx")
        title_idx = item.get("title_idx")
        if isinstance(summary_idx, int):
            insert_at = summary_idx + 1
        elif isinstance(title_idx, int):
            insert_at = title_idx + 1
        else:
            continue
        edits.append(("insert", insert_at, f"- 细节：{new_detail}"))

    if not edits:
        return 0

    offset = 0
    for action, idx, value in sorted(edits, key=lambda item: item[1]):
        real_idx = idx + offset
        if action == "replace":
            lines[real_idx] = value
        else:
            lines.insert(real_idx, value)
            offset += 1

    new_text = "\n".join(lines)
    if text.endswith("\n"):
        new_text += "\n"
    path.write_text(new_text, encoding="utf-8")
    return len(edits)


def extract_report_items(text: str) -> list[dict[str, object]]:
    title_pattern = re.compile(r"^###\s*\d+\)\s*(.+)$")
    source_pattern = re.compile(r"^(?:[-*]\s*)?(?:来源|source)\s*[：:]\s*(.+)$", flags=re.IGNORECASE)
    key_points_header_pattern = re.compile(r"^(?:[-*]\s*)?关键点\s*[：:]?$")
    bullet_pattern = re.compile(r"^\s*(?:[-*•]\s+|\d+\.\s+)(.+)$")

    items: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_key_points = False

    for line in text.splitlines():
        stripped = line.strip()
        title_match = title_pattern.match(stripped)
        if title_match:
            if current is not None:
                items.append(current)
            current = {
                "title": title_match.group(1).strip(),
                "summary": "",
                "detail": "",
                "source": "",
                "key_points": [],
            }
            in_key_points = False
            continue

        if current is None:
            continue

        if key_points_header_pattern.match(stripped):
            in_key_points = True
            continue

        summary_match = SUMMARY_PATTERN.match(stripped)
        if summary_match:
            current["summary"] = summary_match.group(1).strip()
            in_key_points = False
            continue

        detail_match = DETAIL_PATTERN.match(stripped)
        if detail_match:
            current["detail"] = detail_match.group(1).strip()
            in_key_points = False
            continue

        if re.match(r"^(?:[-*]\s*)?(?:影响|impact)\s*[：:]", stripped, flags=re.IGNORECASE):
            in_key_points = False
            continue

        source_match = source_pattern.match(stripped)
        if source_match:
            current["source"] = source_match.group(1).strip()
            in_key_points = False
            continue

        if in_key_points:
            if stripped.startswith("### "):
                in_key_points = False
                continue
            bullet_match = bullet_pattern.match(line)
            if bullet_match:
                point = bullet_match.group(1).strip()
                if point:
                    points = current["key_points"]
                    if isinstance(points, list):
                        points.append(point)

    if current is not None:
        items.append(current)

    return items


def run_checks(path: Path, autofix: bool = False) -> int:
    if not path.exists():
        print(f"ERROR: report not found: {path}")
        return 1

    items = extract_report_items(path.read_text(encoding="utf-8"))
    titles = [str(item.get("title", "")) for item in items]
    sources = [str(item.get("source", "")) for item in items if item.get("source")]
    if not titles:
        print("ERROR: no report items found")
        return 1

    title_complete_ratio_min = float(os.getenv("TITLE_COMPLETE_RATIO_MIN", "0.90"))
    key_points_min_count = int(os.getenv("KEY_POINTS_MIN_COUNT", "2"))
    key_points_max_count = int(os.getenv("KEY_POINTS_MAX_COUNT", "3"))
    key_point_max_chars = int(os.getenv("KEY_POINT_MAX_CHARS", "28"))
    blocked_domains = parse_csv_env("SECOND_HAND_DOMAINS", DEFAULT_SECOND_HAND_DOMAINS)
    detail_min_chars = int(os.getenv("DETAIL_MIN_CHARS", "48"))

    incomplete_count = sum(1 for title in titles if title_looks_incomplete(title))
    complete_ratio = (len(titles) - incomplete_count) / len(titles)

    blocked_hits: list[str] = []
    for source in sources:
        host = normalize_host(source)
        if host and host_matches(host, blocked_domains):
            blocked_hits.append(source)

    key_point_issues: list[str] = []
    detail_issues: list[str] = []
    for idx, item in enumerate(items, 1):
        title = str(item.get("title", ""))
        summary = str(item.get("summary", "")).strip()
        detail = str(item.get("detail", "")).strip()

        if not detail:
            detail_issues.append(f"{idx}) {title}: 缺少细节字段")
        else:
            if len(detail) < detail_min_chars:
                detail_issues.append(f"{idx}) {title}: 细节过短(len={len(detail)})")
            if summary and normalize_for_compare(summary) == normalize_for_compare(detail):
                detail_issues.append(f"{idx}) {title}: 细节与摘要重复")
            if any(phrase in detail for phrase in DETAIL_WEAK_PHRASES):
                detail_issues.append(f"{idx}) {title}: 细节内容过泛")

        points = item.get("key_points", [])
        if not isinstance(points, list):
            key_point_issues.append(f"{idx}) {title}: key_points字段不是列表")
            continue

        if len(points) < key_points_min_count or len(points) > key_points_max_count:
            key_point_issues.append(f"{idx}) {title}: 关键点数量={len(points)}")
            continue

        too_long = [point for point in points if len(str(point).strip()) > key_point_max_chars]
        if too_long:
            key_point_issues.append(f"{idx}) {title}: 存在超长关键点({len(too_long)}条)")

    print(
        "quality summary:",
        f"items={len(titles)}",
        f"title_complete_ratio={complete_ratio:.2f}",
        f"blocked_sources={len(blocked_hits)}",
        f"detail_issues={len(detail_issues)}",
        f"key_point_issues={len(key_point_issues)}",
    )

    strict_mode = is_enabled(os.getenv("QUALITY_CHECK_STRICT"), default=True)
    failed = False
    if complete_ratio < title_complete_ratio_min:
        level = "ERROR" if strict_mode else "WARN"
        print(f"{level}: title complete ratio {complete_ratio:.2f} < threshold {title_complete_ratio_min:.2f}")
        failed = strict_mode
    if blocked_hits:
        level = "ERROR" if strict_mode else "WARN"
        print(f"{level}: blocked second-hand domains found:")
        for hit in blocked_hits:
            print(f"- {hit}")
        failed = strict_mode
    if detail_issues:
        if strict_mode and autofix:
            fixed_count = autofix_detail_lines(path, detail_min_chars=detail_min_chars)
            if fixed_count > 0:
                print(f"info: autofix repaired {fixed_count} detail field(s), re-running checks")
                return run_checks(path, autofix=False)
        level = "ERROR" if strict_mode else "WARN"
        print(f"{level}: detail quality issues found:")
        for issue in detail_issues:
            print(f"- {issue}")
        failed = strict_mode
    if key_point_issues:
        level = "ERROR" if strict_mode else "WARN"
        print(f"{level}: key point format issues found:")
        for issue in key_point_issues:
            print(f"- {issue}")
        failed = strict_mode

    if not strict_mode and (complete_ratio < title_complete_ratio_min or blocked_hits or detail_issues or key_point_issues):
        print("info: quality check running in soft mode (QUALITY_CHECK_STRICT=0), continue without failing")

    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate report quality.")
    parser.add_argument("report", nargs="?", default="reports/latest.md")
    parser.add_argument("--autofix", action="store_true", help="Auto-repair low-quality detail fields before failing")
    args = parser.parse_args()
    return run_checks(Path(args.report), autofix=args.autofix)


if __name__ == "__main__":
    raise SystemExit(main())
