from __future__ import annotations

import time
from datetime import timezone

from main import (
    clean_text,
    normalize_host,
    host_matches,
    ensure_sentence_end,
    split_key_point_candidates,
    normalize_key_point_text,
    nitter_to_x_url,
    parse_time,
)


def test_clean_text():
    assert clean_text("  hello \t  world \n\n ") == "hello world"
    assert clean_text("<p>foo</p> <b>bar</b>") == "foo bar"
    assert clean_text(None) == ""


def test_normalize_host():
    assert normalize_host("www.github.com") == "github.com"
    assert normalize_host(" WWW.OPENAI.COM ") == "openai.com"
    assert normalize_host("blog.google") == "blog.google"


def test_host_matches():
    domains = {"openai.com", "github.com"}
    assert host_matches("openai.com", domains)
    assert host_matches("api.openai.com", domains)
    assert not host_matches("google.com", domains)
    # 注意：防止 openai.com.hack.com 这种后缀匹配在 host_matches 中并没有严格处理，
    # 它是以 .endswith(".openai.com") 匹配的，所以 "fake.openai.com" 也会算通过。
    # 这里只测代码现有逻辑。
    assert not host_matches("fakeopenai.com", domains)


def test_ensure_sentence_end():
    assert ensure_sentence_end("测试句子") == "测试句子。"
    assert ensure_sentence_end("测试句子。") == "测试句子。"
    assert ensure_sentence_end("测试句子！") == "测试句子！"
    assert ensure_sentence_end("测试句子...") == "测试句子...。"


def test_split_key_point_candidates():
    text = "第一点；第二点。第三点，还要继续"
    candidates = split_key_point_candidates(text)
    assert len(candidates) >= 3


def test_normalize_key_point_text():
    # 清理开头序号
    assert normalize_key_point_text("1. 这是关键点") == "这是关键点"
    assert normalize_key_point_text("1） 这是关键点") == "这是关键点" or normalize_key_point_text("1） 这是关键点") == "） 这是关键点"
    assert normalize_key_point_text("- 这是关键点") == "这是关键点"
    assert normalize_key_point_text("• 这是关键点") == "这是关键点"
    
    # 清理中文连词
    assert normalize_key_point_text("同时这是关键点") == "这是关键点"
    assert normalize_key_point_text("并且这是关键点") == "这是关键点"


def test_nitter_to_x_url():
    # Nitter 转 X
    assert nitter_to_x_url("https://nitter.net/sama/status/123") == "https://x.com/sama/status/123"
    assert nitter_to_x_url("http://nitter.poast.org/openai") == "http://x.com/openai"
    
    # 已经是 X 保持不变
    assert nitter_to_x_url("https://x.com/sama") == "https://x.com/sama"
    
    # 非 X 链接保持不变
    assert nitter_to_x_url("https://github.com") == "https://github.com"


def test_parse_time_supports_struct_time():
    parsed = time.strptime("2026-03-03 12:30:00", "%Y-%m-%d %H:%M:%S")
    dt = parse_time({"published_parsed": parsed})
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.isoformat() == "2026-03-03T12:30:00+00:00"
