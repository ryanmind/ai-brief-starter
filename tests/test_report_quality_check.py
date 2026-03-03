from __future__ import annotations

import json

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


def test_quality_check_autofix_repairs_and_passes(tmp_path, monkeypatch):
    report = tmp_path / "report.md"
    report.write_text(REPORT_WITH_DETAIL_ISSUE, encoding="utf-8")
    monkeypatch.setenv("QUALITY_CHECK_STRICT", "1")
    monkeypatch.setenv("DETAIL_MIN_CHARS", "48")
    assert run_checks(report, autofix=True) == 0
    content = report.read_text(encoding="utf-8")
    assert "细节：这是摘要。" not in content
    assert "细节：" in content


def test_quality_check_autofix_fills_missing_summary(tmp_path, monkeypatch):
    report = tmp_path / "report.md"
    report.write_text(
        """# AI 早报

## 详细快讯

### 1) 重申三大使用禁区
- 细节：平台补充了最新使用边界，并强调违规场景会被限制调用。
- 关键点：
  - 补充边界说明
  - 强调违规限制
- 来源：https://openai.com/index/test
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("QUALITY_CHECK_STRICT", "1")
    monkeypatch.setenv("DETAIL_MIN_CHARS", "20")
    assert run_checks(report, autofix=True) == 0
    content = report.read_text(encoding="utf-8")
    assert "- 摘要：" in content


def test_quality_check_missing_source_fails(tmp_path, monkeypatch):
    report = tmp_path / "report.md"
    report.write_text(
        """# AI 早报

## 详细快讯

### 1) 测试标题
- 摘要：这是摘要。
- 细节：这是细节且长度足够用于质检通过。
- 关键点：
  - 关键点一
  - 关键点二
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("QUALITY_CHECK_STRICT", "1")
    assert run_checks(report) == 1


def test_quality_check_outputs_metrics_and_risk_list(tmp_path, monkeypatch):
    report = tmp_path / "report.md"
    report.write_text(
        """# AI 早报

## 详细快讯

### 1) 测试标题
- 摘要：这是摘要。
- 细节：公司完成1.2亿美元融资，2026年收入增长50%，涉及监管审批流程。
- 关键点：
  - 融资信息披露
  - 监管流程推进
- 影响：行业竞争加速。
- 来源：https://openai.com/index/test
""",
        encoding="utf-8",
    )
    metrics_path = tmp_path / "quality_metrics.json"
    risk_path = tmp_path / "high_risk.md"
    monkeypatch.setenv("QUALITY_CHECK_STRICT", "1")
    assert run_checks(report, autofix=True, metrics_output=metrics_path, high_risk_output=risk_path) == 0

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["total_items"] == 1
    assert "repaired_count" in metrics
    assert risk_path.exists()
    assert "高风险条目清单" in risk_path.read_text(encoding="utf-8")
