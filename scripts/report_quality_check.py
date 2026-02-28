#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from urllib.parse import urlparse


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


def parse_csv_env(name: str, defaults: tuple[str, ...]) -> set[str]:
    raw = os.getenv(name)
    values = raw.split(",") if raw else list(defaults)
    return {v.strip().lower() for v in values if v.strip()}


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


def extract_report_items(text: str) -> list[dict[str, object]]:
    title_pattern = re.compile(r"^###\s+\d+\)\s+(.+)$")
    source_pattern = re.compile(r"^- 来源[：:](.+)$")
    key_points_header_pattern = re.compile(r"^- 关键点[：:]$")
    bullet_pattern = re.compile(r"^\s*-\s+(.+)$")

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

        if stripped.startswith("- 摘要") or stripped.startswith("- 影响"):
            in_key_points = False
            continue

        source_match = source_pattern.match(stripped)
        if source_match:
            current["source"] = source_match.group(1).strip()
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

    incomplete_count = sum(1 for title in titles if title_looks_incomplete(title))
    complete_ratio = (len(titles) - incomplete_count) / len(titles)

    blocked_hits: list[str] = []
    for source in sources:
        host = normalize_host(source)
        if host and host_matches(host, blocked_domains):
            blocked_hits.append(source)

    key_point_issues: list[str] = []
    for idx, item in enumerate(items, 1):
        title = str(item.get("title", ""))
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
        f"key_point_issues={len(key_point_issues)}",
    )

    failed = False
    if complete_ratio < title_complete_ratio_min:
        print(
            f"ERROR: title complete ratio {complete_ratio:.2f} < threshold {title_complete_ratio_min:.2f}"
        )
        failed = True
    if blocked_hits:
        print("ERROR: blocked second-hand domains found:")
        for hit in blocked_hits:
            print(f"- {hit}")
        failed = True
    if key_point_issues:
        print("ERROR: key point format issues found:")
        for issue in key_point_issues:
            print(f"- {issue}")
        failed = True

    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate report quality.")
    parser.add_argument("report", nargs="?", default="reports/latest.md")
    args = parser.parse_args()
    return run_checks(Path(args.report))


if __name__ == "__main__":
    raise SystemExit(main())
