from __future__ import annotations

from scripts.report_quality_check import run_checks


REPORT_WITH_DETAIL_ISSUE = """# AI 早报

## 详细快讯

### 1) 测试标题
- 摘要：这是摘要。
- 细节：这是摘要。
- 关键点：
  - 关键点一
  - 关键点二
- 来源：https://openai.com/index/test
"""


def test_quality_check_soft_mode_does_not_fail(tmp_path, monkeypatch):
    report = tmp_path / "report.md"
    report.write_text(REPORT_WITH_DETAIL_ISSUE, encoding="utf-8")
    monkeypatch.setenv("QUALITY_CHECK_STRICT", "0")
    monkeypatch.setenv("DETAIL_MIN_CHARS", "48")
    assert run_checks(report) == 0


def test_quality_check_strict_mode_fails(tmp_path, monkeypatch):
    report = tmp_path / "report.md"
    report.write_text(REPORT_WITH_DETAIL_ISSUE, encoding="utf-8")
    monkeypatch.setenv("QUALITY_CHECK_STRICT", "1")
    monkeypatch.setenv("DETAIL_MIN_CHARS", "48")
    assert run_checks(report) == 1
