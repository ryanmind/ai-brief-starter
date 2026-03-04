from __future__ import annotations

from scripts import render_latest_for_mkdocs


def test_build_mkdocs_latest_generates_collapsible_sections():
    source = """## 📰 AI 早报 · 2026年03月04日12:25:24

### 📌 本期摘要
- 1. 第一条摘要
- 2. 第二条摘要

### 1. 标题A
**摘要**：摘要A
**关键点**
- 要点A1
- 要点A2
**影响分析**：影响A
**来源**：[原文链接](https://example.com/a)

### 2. 标题B
**摘要**：摘要B
**关键点**
- 要点B1
**影响分析**：影响B
**来源**：[原文链接](https://example.com/b)
"""
    rendered = render_latest_for_mkdocs.build_mkdocs_latest(source)

    assert rendered.startswith("# 今日早报")
    assert "更新时间：2026年03月04日12:25:24" in rendered
    assert "1. 第一条摘要" in rendered
    assert "2. 第二条摘要" in rendered
    assert '??? info "1. 标题A"' in rendered
    assert '??? info "2. 标题B"' in rendered
    assert "- **摘要**：摘要A" in rendered
    assert "- **来源**：[原文链接](https://example.com/a)" in rendered


def test_build_mkdocs_latest_handles_missing_sections():
    source = """## 📰 AI 早报 · 2026年03月04日12:25:24

### 1. 只有标题
"""
    rendered = render_latest_for_mkdocs.build_mkdocs_latest(source)

    assert "## 本期摘要" in rendered
    assert "- 暂无摘要" in rendered
    assert '??? info "1. 只有标题"' in rendered
    assert "- **关键点**：" in rendered
    assert "        - 暂无" in rendered


def test_build_mkdocs_latest_supports_legacy_report_shape():
    source = """# AI 早报（2026-02-28）

生成时间：2026-02-28 15:48:56

## 今日要点
- 1. 第一条要点
- 2. 第二条要点

## 详细快讯

### 1) 旧格式标题
- 摘要：旧格式摘要
- 细节：旧格式细节
- 关键点：
  - 关键点1
  - 关键点2
- 影响：旧格式影响
- 来源：https://example.com/legacy
"""
    rendered = render_latest_for_mkdocs.build_mkdocs_latest(source)

    assert "更新时间：2026-02-28 15:48:56" in rendered
    assert "1. 第一条要点" in rendered
    assert '??? info "1. 旧格式标题"' in rendered
    assert "- **细节**：旧格式细节" in rendered
    assert "- **来源**：https://example.com/legacy" in rendered
