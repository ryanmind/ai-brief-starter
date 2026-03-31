from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from scripts import notify_wechat

from src.config import BRIEF_NAME


class FakeResponse:
    def __init__(self, json_data: dict, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._json_data


class TestSendWechatMessage:
    def test_send_wechat_message_success(self):
        with patch("scripts.notify_wechat.requests.post") as mock_post:
            mock_post.return_value = FakeResponse({"code": 0, "message": "success"})
            result = notify_wechat.send_wechat_message(
                title="测试",
                content="测试内容",
                send_key="test-key",
            )
            assert result is True

    def test_send_wechat_message_failure(self):
        with patch("scripts.notify_wechat.requests.post") as mock_post:
            mock_post.return_value = FakeResponse({"code": 1, "message": "failed"})
            result = notify_wechat.send_wechat_message(
                title="测试",
                content="测试内容",
                send_key="test-key",
            )
            assert result is False

    def test_send_wechat_message_request_exception(self):
        with patch("scripts.notify_wechat.requests.post") as mock_post:
            from requests import RequestException

            mock_post.side_effect = RequestException("network error")
            result = notify_wechat.send_wechat_message(
                title="测试",
                content="测试内容",
                send_key="test-key",
            )
            assert result is False


class TestExtractBriefSummary:
    def test_extract_summary_from_bullet_points(self, tmp_path):
        report = tmp_path / "report.md"
        report.write_text(
            f"""# {BRIEF_NAME}

## 本期摘要
- 第一条重要新闻
- 第二条重要新闻
- 第三条重要新闻
""",
            encoding="utf-8",
        )
        summary = notify_wechat.extract_brief_summary(report)
        assert "第一条重要新闻" in summary
        assert "第二条重要新闻" in summary

    def test_extract_summary_from_titles(self, tmp_path):
        report = tmp_path / "report.md"
        report.write_text(
            f"""# {BRIEF_NAME}

### 1. OpenAI 发布新模型 ·
### 2. Claude 代码能力更新 ·
### 3. DeepSeek 开源新项目 ·
""",
            encoding="utf-8",
        )
        summary = notify_wechat.extract_brief_summary(report)
        assert "OpenAI" in summary or "今日要点" in summary

    def test_extract_summary_fallback_when_no_content(self, tmp_path):
        report = tmp_path / "empty.md"
        report.write_text(f"# {BRIEF_NAME}\n", encoding="utf-8")
        summary = notify_wechat.extract_brief_summary(report)
        assert f"{BRIEF_NAME}已生成" in summary

    def test_extract_summary_handles_file_read_error(self, tmp_path):
        report = tmp_path / "nonexistent.md"
        summary = notify_wechat.extract_brief_summary(report)
        assert "报告生成完成" in summary


class TestNotifyNewBrief:
    def test_notify_new_brief_with_doc_url(self, tmp_path):
        report = tmp_path / "report.md"
        report.write_text(
            f"""# {BRIEF_NAME}

## 本期摘要
- 测试新闻
""",
            encoding="utf-8",
        )
        with patch("scripts.notify_wechat.send_wechat_message") as mock_send:
            mock_send.return_value = True
            result = notify_wechat.notify_new_brief(
                report_path=report,
                send_key="test-key",
                doc_url="https://example.com/doc",
            )
            assert result is True
            call_args = mock_send.call_args
            assert f"{BRIEF_NAME}已更新" in call_args.kwargs["title"]
            assert "https://example.com/doc" in call_args.kwargs["content"]

    def test_notify_new_brief_without_doc_url(self, tmp_path):
        report = tmp_path / "report.md"
        report.write_text(
            f"""# {BRIEF_NAME}

## 本期摘要
- 测试新闻
""",
            encoding="utf-8",
        )
        with patch("scripts.notify_wechat.send_wechat_message") as mock_send:
            mock_send.return_value = True
            result = notify_wechat.notify_new_brief(
                report_path=report,
                send_key="test-key",
                doc_url="",
            )
            assert result is True
            call_args = mock_send.call_args
            assert "查看完整文档" not in call_args.kwargs["content"]
