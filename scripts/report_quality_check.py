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


def extract_report_items(text: str) -> tuple[list[str], list[str]]:
    title_pattern = re.compile(r"^###\s+\d+\)\s+(.+)$")
    source_pattern = re.compile(r"^- 来源：(.+)$")
    titles: list[str] = []
    sources: list[str] = []

    for line in text.splitlines():
        title_match = title_pattern.match(line.strip())
        if title_match:
            titles.append(title_match.group(1).strip())
            continue
        source_match = source_pattern.match(line.strip())
        if source_match:
            sources.append(source_match.group(1).strip())

    return titles, sources


def run_checks(path: Path) -> int:
    if not path.exists():
        print(f"ERROR: report not found: {path}")
        return 1

    titles, sources = extract_report_items(path.read_text(encoding="utf-8"))
    if not titles:
        print("ERROR: no report items found")
        return 1

    title_complete_ratio_min = float(os.getenv("TITLE_COMPLETE_RATIO_MIN", "0.90"))
    blocked_domains = parse_csv_env("SECOND_HAND_DOMAINS", DEFAULT_SECOND_HAND_DOMAINS)

    incomplete_count = sum(1 for title in titles if title_looks_incomplete(title))
    complete_ratio = (len(titles) - incomplete_count) / len(titles)

    blocked_hits: list[str] = []
    for source in sources:
        host = normalize_host(source)
        if host and host_matches(host, blocked_domains):
            blocked_hits.append(source)

    print(
        "quality summary:",
        f"items={len(titles)}",
        f"title_complete_ratio={complete_ratio:.2f}",
        f"blocked_sources={len(blocked_hits)}",
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

    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate report quality.")
    parser.add_argument("report", nargs="?", default="reports/latest.md")
    args = parser.parse_args()
    return run_checks(Path(args.report))


if __name__ == "__main__":
    raise SystemExit(main())
