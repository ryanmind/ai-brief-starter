from __future__ import annotations

import main


def test_filter_ai_topic_items_with_stats_keeps_only_ai(monkeypatch):
    monkeypatch.setenv("STRICT_AI_TOPIC_ONLY", "1")
    monkeypatch.setenv("AI_TOPIC_KEYWORDS", "ai,gpt,模型,智能体")
    items = [
        {
            "title": "OpenAI 发布 GPT-5",
            "summary": "新模型支持更强推理",
            "link": "https://openai.com/index/gpt-5",
        },
        {
            "title": "公司周年庆直播活动",
            "summary": "抽奖与福利发布",
            "link": "https://example.com/anniversary",
        },
    ]

    kept, stats = main.filter_ai_topic_items_with_stats(items)
    assert len(kept) == 1
    assert kept[0]["title"] == "OpenAI 发布 GPT-5"
    assert stats.get("non_ai_topic") == 1


def test_filter_ai_topic_items_with_stats_can_be_disabled(monkeypatch):
    monkeypatch.setenv("STRICT_AI_TOPIC_ONLY", "0")
    items = [
        {
            "title": "公司周年庆直播活动",
            "summary": "抽奖与福利发布",
            "link": "https://example.com/anniversary",
        }
    ]
    kept, stats = main.filter_ai_topic_items_with_stats(items)
    assert kept == items
    assert stats.get("strict_mode_disabled") == 1
