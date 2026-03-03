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


def extract_report_items(text: str) -> list[dict[str, object]]:
    title_pattern = re.compile(r"^###\s*\d+\)\s*(.+)$")
    summary_pattern = re.compile(r"^(?:[-*]\s*)?(?:摘要|summary)\s*[：:]\s*(.+)$", flags=re.IGNORECASE)
    detail_pattern = re.compile(r"^(?:[-*]\s*)?(?:细节|详情|detail)\s*[：:]\s*(.+)$", flags=re.IGNORECASE)
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

        summary_match = summary_pattern.match(stripped)
        if summary_match:
            current["summary"] = summary_match.group(1).strip()
            in_key_points = False
            continue

        detail_match = detail_pattern.match(stripped)
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


def run_checks(path: Path) -> int:
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
    args = parser.parse_args()
    return run_checks(Path(args.report))


if __name__ == "__main__":
    raise SystemExit(main())
