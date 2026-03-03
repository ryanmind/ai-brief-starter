from __future__ import annotations

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
