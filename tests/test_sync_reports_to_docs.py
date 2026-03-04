from __future__ import annotations

from pathlib import Path

from scripts import sync_reports_to_docs


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_sync_reports_to_docs_updates_latest_and_history(tmp_path, monkeypatch):
    reports_dir = tmp_path / "reports"
    docs_dir = tmp_path / "docs"

    latest_report = """## 📰 AI 早报 · 2026年03月04日12:25:24

### 📌 本期摘要
- 1. 今日摘要A
### 1. 标题A
**摘要**：摘要A
**关键点**
- 要点A
**影响分析**：影响A
**来源**：[原文链接](https://example.com/a)
"""
    archived_report = """# AI 早报（2026-03-04）

生成时间：2026-03-04 12:25:24

## 今日要点
- 1. 历史摘要A

## 详细快讯

### 1) 历史标题A
- 摘要：历史摘要A
- 细节：历史细节A
- 关键点：
  - 历史要点A
- 影响：历史影响A
- 来源：https://example.com/history-a
"""
    _write(reports_dir / "latest.md", latest_report)
    _write(reports_dir / "2026-03-04.md", archived_report)
    _write(docs_dir / "history" / "2026-03-03.md", "# 旧归档\n")

    monkeypatch.setattr(sync_reports_to_docs, "current_sync_time", lambda: "2026年03月04日23:59:59")
    sync_reports_to_docs.sync_reports_to_docs(reports_dir=reports_dir, docs_dir=docs_dir)

    latest_page = (docs_dir / "latest.md").read_text(encoding="utf-8")
    history_page = (docs_dir / "history" / "2026-03-04.md").read_text(encoding="utf-8")
    history_index = (docs_dir / "history.md").read_text(encoding="utf-8")

    assert latest_page.startswith("# 今日早报")
    assert "更新时间：2026年03月04日23:59:59" in latest_page
    assert "1. 今日摘要A" in latest_page
    assert history_page.startswith("# AI 早报归档 · 2026-03-04")
    assert "历史细节A" not in history_page
    assert "- [2026-03-04](history/2026-03-04.md)" in history_index
    assert "- [2026-03-03](history/2026-03-03.md)" in history_index
