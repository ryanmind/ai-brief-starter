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


def find_latest_dated_report(directory: Path) -> tuple[str, Path] | None:
    if not directory.exists():
        return None
    dated_files = sorted(
        [path for path in directory.glob("*.md") if DATE_REPORT_PATTERN.match(path.name)],
        key=lambda item: item.stem,
        reverse=True,
    )
    if not dated_files:
        return None
    latest = dated_files[0]
    return latest.stem, latest


def update_latest_page(reports_dir: Path, docs_dir: Path) -> None:
    latest_page = docs_dir / "latest.md"
    latest_report = reports_dir / "latest.md"
    latest_report_date = find_latest_dated_report(reports_dir)
    latest_history_date = find_latest_dated_report(docs_dir / "history")

    # Avoid accidentally regressing docs/latest.md when local reports are stale.
    if latest_history_date and (
        latest_report_date is None or latest_history_date[0] > latest_report_date[0]
    ):
        latest_page.write_text(
            with_page_title(
                latest_history_date[1].read_text(encoding="utf-8"),
                title="今日早报",
            ),
            encoding="utf-8",
        )
        return

    if latest_report.exists():
        source = latest_report
    elif latest_report_date:
        source = latest_report_date[1]
    elif latest_history_date:
        latest_page.write_text(
            with_page_title(
                latest_history_date[1].read_text(encoding="utf-8"),
                title="今日早报",
            ),
            encoding="utf-8",
        )
        return
    else:
        raise FileNotFoundError(
            f"no source found for latest page: reports={reports_dir}, docs={docs_dir}"
        )

    content = source.read_text(encoding="utf-8")
    rendered = build_mkdocs_latest(content, updated_at_override=current_sync_time())
    latest_page.write_text(with_page_title(rendered, title="今日早报"), encoding="utf-8")


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
    has_latest = (reports_dir / "latest.md").exists()
    has_dated_report = find_latest_dated_report(reports_dir) is not None
    has_history_report = find_latest_dated_report(docs_dir / "history") is not None
    if not (has_latest or has_dated_report or has_history_report):
        raise FileNotFoundError(
            f"latest report missing under reports ({reports_dir}) and docs history ({docs_dir / 'history'})"
        )
    sync_reports_to_docs(reports_dir=reports_dir, docs_dir=docs_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
