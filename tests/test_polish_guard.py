from __future__ import annotations

import os
import main
from main import polish_result_is_safe
from src.config import LLM_MODEL_DEFAULT


def test_polish_result_is_safe_rejects_structure_drift():
    original = """# AI 快讯（2026-03-03）

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
    polished = """# AI 快讯（2026-03-03）

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
    original = """# AI 快讯（2026-03-03）

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
    polished = """# AI 快讯（2026-03-03）

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
    original = """## 📰 AI 快讯 · 2026年03月03日12:00:00

### 1. 标题
**摘要**：摘要句子。
**关键点**
- 要点一
- 要点二
**影响分析**：影响句子。
**来源**：[原文链接](https://example.com/a)
"""
    unsafe_polished = """## 📰 AI 快讯 · 2026年03月03日12:00:00

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
        llm_api_key="test-key",
        llm_model=LLM_MODEL_DEFAULT,
    )
    assert result == original


def test_polish_markdown_with_llm_accepts_safe_output(monkeypatch):
    # src/llm.py is the actual module containing polish_markdown_with_llm, src.llm is the package
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "src_llm_py",
        os.path.join(os.path.dirname(__file__), "..", "src", "llm.py")
    )
    src_llm_py = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(src_llm_py)

    monkeypatch.setenv("FINAL_POLISH_ENABLED", "1")
    original = """## 📰 AI 快讯 · 2026年03月03日12:00:00

### 1. 标题
**摘要**：摘要句子。
**关键点**
- 要点一
- 要点二
**影响分析**：影响句子。
**来源**：[原文链接](https://example.com/a)
"""
    safe_polished = """## 📰 AI 快讯 · 2026年03月03日12:00:00

### 1. 标题
**摘要**：摘要句子，更凝练。
**关键点**
- 要点一
- 要点二
**影响分析**：影响句子，更清晰。
**来源**：[原文链接](https://example.com/a)
"""
    # Monkeypatch the actual module that polish_markdown_with_llm uses
    monkeypatch.setattr(src_llm_py, "llm_chat", lambda **kwargs: f"```markdown\n{safe_polished}\n```")

    # main.polish_markdown_with_llm is just a reference anyway, get it from the actual module
    result = src_llm_py.polish_markdown_with_llm(
        markdown=original,
        llm_api_key="test-key",
        llm_model=LLM_MODEL_DEFAULT,
    )
    assert result.strip() == safe_polished.strip()
