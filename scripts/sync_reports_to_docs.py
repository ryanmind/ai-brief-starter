#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

try:
    from scripts.render_latest_for_mkdocs import build_mkdocs_latest
except ModuleNotFoundError:  # pragma: no cover - CLI entrypoint fallback
    from render_latest_for_mkdocs import build_mkdocs_latest


DATE_REPORT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.md$")


def with_page_title(markdown: str, title: str) -> str:
    lines = markdown.splitlines()
    if lines and lines[0].startswith("# "):
        lines[0] = f"# {title}"
    return "\n".join(lines).rstrip() + "\n"


def render_report(report_path: Path, title: str) -> str:
    content = report_path.read_text(encoding="utf-8")
    rendered = build_mkdocs_latest(content)
    return with_page_title(rendered, title=title)


def current_sync_time() -> str:
    return datetime.now().strftime("%Y年%m月%d日%H:%M:%S")


def update_latest_page(reports_dir: Path, docs_dir: Path) -> None:
    latest_report = reports_dir / "latest.md"
    latest_page = docs_dir / "latest.md"
    content = latest_report.read_text(encoding="utf-8")
    rendered = build_mkdocs_latest(content, updated_at_override=current_sync_time())
    latest_page.write_text(
        with_page_title(rendered, title="今日早报"),
        encoding="utf-8",
    )


def update_history_pages(reports_dir: Path, docs_dir: Path) -> None:
    history_dir = docs_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    for report in sorted(reports_dir.iterdir()):
        if not report.is_file():
            continue
        if not DATE_REPORT_PATTERN.match(report.name):
            continue
        date = report.stem
        target = history_dir / f"{date}.md"
        target.write_text(
            render_report(report, title=f"AI 早报归档 · {date}"),
            encoding="utf-8",
        )


def build_history_index(docs_dir: Path, max_items: int = 120) -> None:
    history_dir = docs_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_files = sorted(
        [path for path in history_dir.glob("*.md") if DATE_REPORT_PATTERN.match(path.name)],
        key=lambda item: item.stem,
        reverse=True,
    )

    lines: list[str] = [
        "# 历史早报归档",
        "",
        "> 最新一期请查看 [今日早报](latest.md)。",
        "",
    ]

    if not history_files:
        lines.extend(["暂无历史归档。", ""])
    else:
        lines.append("## 按日期浏览")
        lines.append("")
        for path in history_files[:max_items]:
            date = path.stem
            lines.append(f"- [{date}](history/{date}.md)")
        lines.append("")

    (docs_dir / "history.md").write_text("\n".join(lines), encoding="utf-8")


def sync_reports_to_docs(reports_dir: Path, docs_dir: Path) -> None:
    update_latest_page(reports_dir=reports_dir, docs_dir=docs_dir)
    update_history_pages(reports_dir=reports_dir, docs_dir=docs_dir)
    build_history_index(docs_dir=docs_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync generated reports to docs pages.")
    parser.add_argument("--reports-dir", default="reports", help="Directory containing generated reports")
    parser.add_argument("--docs-dir", default="docs", help="Directory containing mkdocs pages")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    reports_dir = Path(args.reports_dir)
    docs_dir = Path(args.docs_dir)
    latest_report = reports_dir / "latest.md"
    if not latest_report.exists():
        raise FileNotFoundError(f"latest report missing: {latest_report}")
    sync_reports_to_docs(reports_dir=reports_dir, docs_dir=docs_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
