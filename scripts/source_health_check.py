#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import main


def normalize_host(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    return host[4:] if host.startswith("www.") else host


def format_dt(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def check_sources() -> tuple[list[dict[str, str]], int]:
    results: list[dict[str, str]] = []
    failed = 0
    sources = main.load_sources("sources.txt")
    cutoff = datetime(1970, 1, 1, tzinfo=timezone.utc)

    for source in sources:
        try:
            _, entries, error = main._fetch_single_source(source=source, cutoff=cutoff, per_source=20)
            latest_dt = None
            for entry in entries[:20]:
                published_raw = str(entry.get("published", "")).strip()
                if not published_raw:
                    continue
                try:
                    published = datetime.fromisoformat(published_raw)
                except ValueError:
                    continue
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
                if published and (latest_dt is None or published > latest_dt):
                    latest_dt = published

            if error:
                failed += 1
                results.append(
                    {
                        "source": source,
                        "host": normalize_host(source),
                        "entries": "0",
                        "latest": "-",
                        "status": "FAIL",
                        "reason": str(error),
                    }
                )
                continue

            results.append(
                {
                    "source": source,
                    "host": normalize_host(source),
                    "entries": str(len(entries)),
                    "latest": format_dt(latest_dt),
                    "status": "OK",
                    "reason": "",
                }
            )
        except Exception as exc:
            failed += 1
            results.append(
                {
                    "source": source,
                    "host": normalize_host(source),
                    "entries": "0",
                    "latest": "-",
                    "status": "FAIL",
                    "reason": str(exc),
                }
            )

    return results, failed


def to_markdown(rows: list[dict[str, str]], checked_at: str) -> str:
    lines = [
        "# Source Health Check",
        "",
        f"- Checked at: {checked_at}",
        f"- Total sources: {len(rows)}",
        "",
        "| Host | Entries | Latest | Status | Source | Reason |",
        "|---|---:|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['host']} | {row['entries']} | {row['latest']} | {row['status']} | {row['source']} | {row['reason']} |"
        )
    return "\n".join(lines) + "\n"


def main_cli() -> int:
    parser = argparse.ArgumentParser(description="Check RSS/Atom source health.")
    parser.add_argument("--output", default="", help="Optional markdown output path")
    args = parser.parse_args()

    rows, failed = check_sources()
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report = to_markdown(rows, checked_at)
    print(report)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

    if failed == len(rows):
        print("ERROR: all sources failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
