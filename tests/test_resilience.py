from __future__ import annotations

import base64
import hashlib
import hmac
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
