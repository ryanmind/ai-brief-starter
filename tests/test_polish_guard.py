from __future__ import annotations

import main
from main import polish_result_is_safe


def test_polish_result_is_safe_rejects_structure_drift():
    original = """# AI 早报（2026-03-03）

## 详细快讯

### 1) 标题
- 摘要：摘要句子。
- 细节：细节句子。
- 关键点：
  - 要点一
  - 要点二
- 影响：影响句子。
- 来源：https://example.com/a
"""
    polished = """# AI 早报（2026-03-03）

## 详细快讯

### 1) 标题
- 摘要：摘要句子。
- 关键点：
  - 要点一
  - 要点二
- 影响：影响句子。
- 来源：https://example.com/a
"""
    assert not polish_result_is_safe(original, polished)


def test_polish_result_is_safe_accepts_same_structure():
    original = """# AI 早报（2026-03-03）

## 详细快讯

### 1) 标题
- 摘要：摘要句子。
- 细节：细节句子。
- 关键点：
  - 要点一
  - 要点二
- 影响：影响句子。
- 来源：https://example.com/a
"""
    polished = """# AI 早报（2026-03-03）

## 详细快讯

### 1) 标题
- 摘要：摘要句子。
- 细节：细节句子。
- 关键点：
  - 要点一
  - 要点二
- 影响：影响句子。
- 来源：https://example.com/a
"""
    assert polish_result_is_safe(original, polished)


def test_polish_markdown_with_llm_rejects_unsafe_output(monkeypatch):
    monkeypatch.setenv("FINAL_POLISH_ENABLED", "1")
    original = """## 📰 AI 早报 · 2026年03月03日12:00:00

### 1. 标题
**摘要**：摘要句子。
**关键点**
- 要点一
- 要点二
**影响分析**：影响句子。
**来源**：[原文链接](https://example.com/a)
"""
    unsafe_polished = """## 📰 AI 早报 · 2026年03月03日12:00:00

### 1. 标题
**摘要**：摘要句子。
**关键点**
- 要点一
- 要点二
**影响分析**：影响句子。
"""
    monkeypatch.setattr(main, "llm_chat", lambda **kwargs: unsafe_polished)

    result = main.polish_markdown_with_llm(
        markdown=original,
        qwen_api_key="test-key",
        qwen_model="qwen-flash",
    )
    assert result == original


def test_polish_markdown_with_llm_accepts_safe_output(monkeypatch):
    monkeypatch.setenv("FINAL_POLISH_ENABLED", "1")
    original = """## 📰 AI 早报 · 2026年03月03日12:00:00

### 1. 标题
**摘要**：摘要句子。
**关键点**
- 要点一
- 要点二
**影响分析**：影响句子。
**来源**：[原文链接](https://example.com/a)
"""
    safe_polished = """## 📰 AI 早报 · 2026年03月03日12:00:00

### 1. 标题
**摘要**：摘要句子，更凝练。
**关键点**
- 要点一
- 要点二
**影响分析**：影响句子，更清晰。
**来源**：[原文链接](https://example.com/a)
"""
    monkeypatch.setattr(main, "llm_chat", lambda **kwargs: f"```markdown\n{safe_polished}\n```")

    result = main.polish_markdown_with_llm(
        markdown=original,
        qwen_api_key="test-key",
        qwen_model="qwen-flash",
    )
    assert result.strip() == safe_polished.strip()
