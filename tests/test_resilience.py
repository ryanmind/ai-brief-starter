from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
from concurrent.futures import TimeoutError as FuturesTimeoutError
from types import SimpleNamespace

import main
from scripts import notify_feishu


def test_build_feishu_sign_matches_official_formula(monkeypatch):
    monkeypatch.setattr(notify_feishu.time, "time", lambda: 1700000000)
    timestamp, sign = notify_feishu.build_feishu_sign("bot-secret")
    expected = base64.b64encode(
        hmac.new(f"{timestamp}\nbot-secret".encode("utf-8"), digestmod=hashlib.sha256).digest()
    ).decode("utf-8")
    assert sign == expected


def test_fetch_items_timeout_is_graceful(monkeypatch):
    monkeypatch.setattr(
        main,
        "_fetch_single_source",
        lambda source, cutoff, per_source: (
            source,
            [
                {
                    "title": "A",
                    "link": "https://example.com/a",
                    "summary": "s",
                    "published": "",
                }
            ],
            None,
        ),
    )

    def timeout_as_completed(_futures, timeout):
        raise FuturesTimeoutError()

    monkeypatch.setattr(main, "as_completed", timeout_as_completed)

    items = main.fetch_items(sources=["https://example.com/rss"], hours=24, per_source=1, max_workers=1)
    assert items == []


def test_fetch_items_timeout_shutdown_without_wait(monkeypatch):
    created_executors = []

    class DummyFuture:
        def __init__(self):
            self.cancelled = False

        def done(self):
            return self.cancelled

        def cancel(self):
            self.cancelled = True
            return True

    class DummyExecutor:
        def __init__(self, *args, **kwargs):
            self.shutdown_calls = []
            created_executors.append(self)

        def submit(self, fn, source, cutoff, per_source):
            return DummyFuture()

        def shutdown(self, wait=True, cancel_futures=False):
            self.shutdown_calls.append((wait, cancel_futures))

    def timeout_as_completed(_futures, timeout):
        raise FuturesTimeoutError()

    monkeypatch.setattr(main, "ThreadPoolExecutor", DummyExecutor)
    monkeypatch.setattr(main, "as_completed", timeout_as_completed)

    items = main.fetch_items(sources=["https://example.com/rss"], hours=24, per_source=1, max_workers=1)
    assert items == []
    assert created_executors
    assert created_executors[0].shutdown_calls[-1] == (False, True)


def test_rank_and_summarize_fallback_on_llm_exception(monkeypatch):
    source_items = [
        {
            "title": "OpenAI 发布新模型",
            "link": "https://openai.com/news/model",
            "summary": "OpenAI 发布新模型，提升推理能力。",
            "published": "2026-03-03T00:00:00+00:00",
        }
    ]

    def boom(**_kwargs):
        raise RuntimeError("temporary upstream failure")

    monkeypatch.setattr(main, "llm_chat", boom)

    result = main.rank_and_summarize(
        items=source_items,
        qwen_api_key="test-key",
        qwen_model="qwen-flash",
        top_n=1,
    )

    assert len(result) == 1
    assert result[0]["title"] == "OpenAI 发布新模型"
    assert result[0]["impact"]
    assert "建议查看原文" not in result[0]["impact"]


def test_fetch_single_source_github_changelog_fallback(monkeypatch):
    source = "https://github.com/ByteDance-Seed/Seed-VC/commits/main/CHANGELOG.md.atom"

    def fake_parse(url):
        if url.endswith("CHANGELOG.md.atom"):
            return SimpleNamespace(entries=[], bozo=1, bozo_exception=Exception("syntax error"))
        if url.endswith("/releases.atom"):
            return SimpleNamespace(
                entries=[
                    {
                        "title": "v1.0.0",
                        "link": "https://github.com/ByteDance-Seed/Seed-VC/releases/tag/v1.0.0",
                        "summary": "release notes",
                        "published": "2026-03-03T00:00:00Z",
                    }
                ],
                bozo=0,
            )
        return SimpleNamespace(entries=[], bozo=0)

    monkeypatch.setattr(main.feedparser, "parse", fake_parse)

    _, items, error = main._fetch_single_source(
        source=source,
        cutoff=main.datetime(2026, 3, 1, tzinfo=main.timezone.utc),
        per_source=5,
    )
    assert error is None
    assert len(items) == 1
    assert items[0]["link"].endswith("/releases/tag/v1.0.0")


def test_history_dedupe_prefers_dedupe_link():
    item = {
        "title": "更新日志更新",
        "link": "https://github.com/example/project/blob/main/CHANGELOG.md",
        "dedupe_link": "https://github.com/example/project/commit/abcdef1",
        "summary": "更新了 changelog",
        "published": "",
    }
    blob_fp = f"l:{main.normalize_link_for_dedupe(item['link'])}"
    commit_fp = f"l:{main.normalize_link_for_dedupe(item['dedupe_link'])}"

    kept, dropped = main.filter_items_by_history([item], {blob_fp})
    assert dropped == 0
    assert len(kept) == 1

    kept, dropped = main.filter_items_by_history([item], {commit_fp})
    assert dropped == 1
    assert kept == []


def test_sync_markdown_to_new_doc_skips_unreadable_link(monkeypatch):
    monkeypatch.setenv("FEISHU_APP_ID", "app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret")
    monkeypatch.setenv("FEISHU_DOC_PUBLIC_READABLE", "1")
    monkeypatch.setenv("FEISHU_DOC_PUBLIC_REQUIRED", "0")

    monkeypatch.setattr(notify_feishu, "get_tenant_access_token", lambda app_id, app_secret: "token")
    monkeypatch.setattr(
        notify_feishu,
        "create_docx_document",
        lambda token, title, folder_token: ("doc-id", "https://tenant.feishu.cn/docx/doc-id"),
    )
    monkeypatch.setattr(notify_feishu, "configure_docx_public_permission", lambda token, document_id: False)
    monkeypatch.setattr(notify_feishu, "create_docx_children", lambda token, document_id, lines: None)

    url = notify_feishu.sync_markdown_to_new_doc(markdown="# 标题", title="标题")
    assert url == ""


def test_sync_markdown_to_new_doc_prefers_api_returned_url(monkeypatch):
    monkeypatch.setenv("FEISHU_APP_ID", "app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "secret")
    monkeypatch.setenv("FEISHU_DOC_PUBLIC_READABLE", "1")
    monkeypatch.setenv("FEISHU_DOC_PUBLIC_REQUIRED", "1")

    monkeypatch.setattr(notify_feishu, "get_tenant_access_token", lambda app_id, app_secret: "token")
    monkeypatch.setattr(
        notify_feishu,
        "create_docx_document",
        lambda token, title, folder_token: ("doc-id", "https://tenant.feishu.cn/docx/doc-id"),
    )
    monkeypatch.setattr(notify_feishu, "configure_docx_public_permission", lambda token, document_id: True)
    monkeypatch.setattr(notify_feishu, "create_docx_children", lambda token, document_id, lines: None)

    url = notify_feishu.sync_markdown_to_new_doc(markdown="# 标题", title="标题")
    assert url == "https://tenant.feishu.cn/docx/doc-id"


def test_is_public_readable_state_handles_v2_nested_shape():
    response = {
        "code": 0,
        "data": {
            "permission_public": {
                "external_access_entity": "open",
                "link_share_entity": "anyone_readable",
            }
        },
    }
    assert notify_feishu.is_public_readable_state(response) is True


def test_markdown_to_text_blocks_keeps_ordered_list_without_bullet():
    markdown = """# AI 早报

## 30秒导读
- 1. 第一条
- 2. 第二条
"""
    blocks = notify_feishu.markdown_to_text_blocks(markdown)
    assert "1. 第一条" in blocks
    assert "2. 第二条" in blocks
    assert "• 1. 第一条" not in blocks


def test_render_markdown_hides_empty_field_lines():
    markdown = main.render_markdown(
        [
            {
                "title": "测试条目",
                "brief": "",
                "details": "",
                "impact": "",
                "key_points": [],
                "link": "",
            }
        ]
    )
    assert "**摘要**：" not in markdown
    assert "**细节**：" not in markdown
    assert "**关键点**" not in markdown
    assert "**影响分析**：" not in markdown
    assert "**来源**：" not in markdown


def test_localize_items_to_chinese_ignores_placeholder_fields(monkeypatch):
    items = [
        {
            "title": "OpenAI 发布新模型",
            "brief": "原始细节，包含能力更新与发布时间。",
            "details": "原始细节，包含能力更新与发布时间。",
            "impact": "原始影响",
            "summary": "原始细节，包含能力更新与发布时间。",
            "key_points": ["原始要点一", "原始要点二"],
            "link": "https://openai.com/news/model",
            "published": "2026-03-03T00:00:00+00:00",
        }
    ]
    monkeypatch.setattr(
        main,
        "llm_chat",
        lambda **kwargs: json.dumps(
            {
                "items": [
                    {
                        "id": 1,
                        "title": "none",
                        "brief": "value",
                        "details": "null",
                        "impact": "n/a",
                        "key_points": ["value", "none"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
    )

    localized = main.localize_items_to_chinese(
        items=items,
        qwen_api_key="test-key",
        qwen_model="qwen-flash",
    )
    assert localized[0]["title"] == "OpenAI 发布新模型"
    assert "value" not in localized[0]["brief"].lower()
    assert "原始细节" in localized[0]["brief"]
    assert "原始细节" in localized[0]["details"]
    assert localized[0]["impact"] == "原始影响"


def test_render_markdown_compacts_field_spacing():
    markdown = main.render_markdown(
        [
            {
                "title": "测试条目",
                "brief": "这是摘要",
                "details": "这是细节（内部字段，不应直接渲染）",
                "impact": "这是影响",
                "key_points": ["要点一", "要点二"],
                "link": "https://example.com",
            }
        ]
    )
    assert "**细节**：" not in markdown
    assert "\n\n**影响分析**：" not in markdown
    assert "\n\n**来源**：" not in markdown


def test_render_markdown_drops_empty_placeholder_summary_line():
    markdown = main.render_markdown(
        [
            {
                "title": "测试条目",
                "brief": "( )。",
                "details": "内部细节",
                "impact": "这是影响",
                "key_points": ["要点一", "要点二"],
                "link": "https://example.com",
            }
        ]
    )
    assert "**摘要**：" not in markdown


def test_render_markdown_drops_placeholder_key_points_without_extra_blank_lines():
    markdown = main.render_markdown(
        [
            {
                "title": "测试条目",
                "brief": "这是摘要",
                "details": "内部细节",
                "impact": "这是影响",
                "key_points": ["关键点：value", "要点：value", "value"],
                "link": "https://example.com",
            }
        ]
    )
    assert "**关键点**" not in markdown
    assert "关键点：value" not in markdown
    assert "\n\n\n" not in markdown


def test_render_markdown_removes_entry_separator_and_keeps_single_gap_between_items():
    markdown = main.render_markdown(
        [
            {
                "title": "条目一",
                "brief": "摘要一",
                "details": "内部细节一",
                "impact": "影响一",
                "key_points": ["要点一", "要点二"],
                "link": "https://example.com/1",
            },
            {
                "title": "条目二",
                "brief": "摘要二",
                "details": "内部细节二",
                "impact": "影响二",
                "key_points": ["要点三", "要点四"],
                "link": "https://example.com/2",
            },
        ]
    )
    assert "---" not in markdown
    assert "\n\n\n### 2." not in markdown
    assert "\n**来源**：[原文链接](https://example.com/1)\n\n### 2. 条目二" in markdown


def test_main_quality_check_fail_open_keeps_pipeline_running(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QWEN_API_KEY", "test-key")
    monkeypatch.setenv("QUALITY_CHECK_FAIL_OPEN", "1")
    monkeypatch.setenv("FINAL_POLISH_ENABLED", "0")
    monkeypatch.setenv("TOP_N", "5")
    monkeypatch.setenv("MAX_ITEMS", "10")

    item = {
        "title": "OpenAI 发布新模型",
        "link": "https://openai.com/news/new-model",
        "summary": "官方发布新模型并更新能力说明。",
        "published": "2026-03-03T00:00:00+00:00",
    }
    selected_item = {
        **item,
        "brief": "OpenAI 发布新模型并披露关键能力升级。",
        "details": "官方说明包含模型能力更新与适用范围。",
        "impact": "有助于开发者更快落地相关应用。",
        "score": "100",
        "key_points": ["官方已发布", "包含能力升级"],
    }

    monkeypatch.setattr(main, "load_sources", lambda path="sources.txt": ["https://openai.com/news/rss.xml"])
    monkeypatch.setattr(main, "fetch_items", lambda **kwargs: [item])
    monkeypatch.setattr(main, "rank_and_summarize", lambda **kwargs: [selected_item])
    monkeypatch.setattr(main, "localize_items_to_chinese", lambda items, **kwargs: items)
    monkeypatch.setattr(main, "check_category_balance", lambda items: {})

    calls: list[bool] = []

    def fake_run_quality_checks(*, path, autofix, metrics_output=None, high_risk_output=None):
        calls.append(autofix)
        if metrics_output is not None:
            Path(metrics_output).write_text('{"failure_reasons":{"structure_missing":1}}', encoding="utf-8")
        if high_risk_output is not None:
            Path(high_risk_output).write_text("# 高风险条目清单\n", encoding="utf-8")
        return 1

    monkeypatch.setattr(main, "run_quality_checks", fake_run_quality_checks)

    main.main()

    assert calls == [True]
    assert (tmp_path / "reports/latest.md").exists()


def test_main_quality_check_fail_open_disabled_still_continues(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QWEN_API_KEY", "test-key")
    monkeypatch.setenv("QUALITY_CHECK_FAIL_OPEN", "0")
    monkeypatch.setenv("FINAL_POLISH_ENABLED", "0")
    monkeypatch.setenv("TOP_N", "5")
    monkeypatch.setenv("MAX_ITEMS", "10")

    item = {
        "title": "OpenAI 发布新模型",
        "link": "https://openai.com/news/new-model",
        "summary": "官方发布新模型并更新能力说明。",
        "published": "2026-03-03T00:00:00+00:00",
    }
    selected_item = {
        **item,
        "brief": "OpenAI 发布新模型并披露关键能力升级。",
        "details": "官方说明包含模型能力更新与适用范围。",
        "impact": "有助于开发者更快落地相关应用。",
        "score": "100",
        "key_points": ["官方已发布", "包含能力升级"],
    }

    monkeypatch.setattr(main, "load_sources", lambda path="sources.txt": ["https://openai.com/news/rss.xml"])
    monkeypatch.setattr(main, "fetch_items", lambda **kwargs: [item])
    monkeypatch.setattr(main, "rank_and_summarize", lambda **kwargs: [selected_item])
    monkeypatch.setattr(main, "localize_items_to_chinese", lambda items, **kwargs: items)
    monkeypatch.setattr(main, "check_category_balance", lambda items: {})
    monkeypatch.setattr(main, "run_quality_checks", lambda **kwargs: 1)

    main.main()
    assert (tmp_path / "reports/latest.md").exists()


def test_build_quality_warning_lines_reads_merged_quality_metrics(tmp_path):
    report = tmp_path / "latest.md"
    report.write_text("# AI 早报\n", encoding="utf-8")
    metrics = {
        "quality_check": {
            "passed": False,
            "failure_reasons": {"detail_quality": 2, "missing_source": 1},
            "repaired_count": 3,
        }
    }
    (tmp_path / "quality_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False), encoding="utf-8")

    lines = notify_feishu.build_quality_warning_lines(report)
    assert any("质检提醒" in line for line in lines)
    assert any("detail_quality：2" in line for line in lines)
    assert any("自动修复：3 处" in line for line in lines)
