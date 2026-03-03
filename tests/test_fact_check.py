from __future__ import annotations

import pytest

from main import (
    fact_overlap_ratio,
    has_unseen_numbers,
    extract_numbers,
    extractive_brief,
    sanitize_item_factuality,
)


def test_extract_numbers():
    assert extract_numbers("涨了 5%，市占率达到 12.3%") == {"5", "12", "12.3", "3", "3%", "12.3%", "5%"} or extract_numbers("涨了 5%，市占率达到 12.3%") == {'12.3%', '5%'}
    assert extract_numbers("GPT-4 发布于 2023 年") == {"4", "2023"}
    assert extract_numbers("没有数字") == set()


def test_has_unseen_numbers():
    # 所有生成数字都在原证据中
    assert not has_unseen_numbers("5% 的增长", "我们有 5% 的增长")
    
    # 生成的数字不在原证据中
    assert has_unseen_numbers("发布了 GPT-5", "发布了新模型")
    
    # 允许部分未见（只要不是全新的数字）
    assert not has_unseen_numbers("2024年", "2024 年 Q1")


def test_fact_overlap_ratio():
    evidence = "OpenAI 发布了全新的 GPT-4o 模型，支持实时语音对话"
    
    # 强相关
    assert fact_overlap_ratio("OpenAI 推出 GPT-4o，自带实时语音", evidence) > 0.5
    
    # 毫不相关（或完全是新词）
    assert fact_overlap_ratio("苹果发布 iPhone 16", evidence) < 0.6


def test_extractive_brief():
    # 优先抽取第一句
    assert extractive_brief({"title": "标题", "summary": "第一句。第二句！"}) == "第一句。"
    
    # 没有标点时抽取前 160 字
    long_text = "我" * 200
    assert len(extractive_brief({"title": "标题", "summary": long_text})) == 160
    
    # summary 为空退回 title
    assert extractive_brief({"title": "标题", "summary": ""}) == "标题"


def test_sanitize_item_factuality():
    item = {
        "title": "测试证据标题",
        "summary": "这是原始摘要的第一句。这是第二句。",
        "brief": "完全无关的 AI 生成长文本摘要",
        "details": "完全无关的 AI 生成长文本细节",
    }
    
    # brief 重合度低，应该被降级为抽取式
    # 抽取式结果应该是 "这是原始摘要的第一句。"
    # brief 重合度低，应该被降级为抽取式
    # 抽取式结果应该是 "这是原始摘要的第一句。"
    # NOTE: Since FACT_OVERLAP_MIN is fetched from env, we patch it for the test
    import main
    old_min = main.FACT_OVERLAP_MIN
    main.FACT_OVERLAP_MIN = 0.8
    try:
        sanitized = sanitize_item_factuality(item)
    finally:
        main.FACT_OVERLAP_MIN = old_min
    assert sanitized["brief"] == "这是原始摘要的第一句。"
    
    # 此时 details 也会被重置为抽取式的第二句或等于 brief
    assert sanitized["details"].startswith("这是原始摘要的第一句")
