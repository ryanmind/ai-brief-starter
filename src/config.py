"""Shared configuration constants and environment helpers.

This module is the single source of truth for constants used by
main.py, report_quality_check.py, and source_health_check.py.
"""
from __future__ import annotations

import os
import re


def int_env(name: str, default: int, min_value: int = 1, max_value: int = 1000) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(min_value, min(max_value, value))


def float_env(name: str, default: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(min_value, min(max_value, value))


def parse_csv_env(name: str, default_values: tuple[str, ...]) -> set[str]:
    raw = os.getenv(name)
    values = raw.split(",") if raw is not None else list(default_values)
    return {value.strip().lower() for value in values if value.strip()}


# ---- Content length limits ----

BRIEF_MAX_CHARS = int_env("BRIEF_MAX_CHARS", 160, min_value=40, max_value=400)
IMPACT_MAX_CHARS = int_env("IMPACT_MAX_CHARS", 140, min_value=40, max_value=320)
DETAIL_MAX_CHARS = int_env("DETAIL_MAX_CHARS", 260, min_value=80, max_value=800)
DETAIL_MIN_CHARS = int_env("DETAIL_MIN_CHARS", 48, min_value=20, max_value=200)
TITLE_MAX_CHARS = 50
KEY_POINTS_MAX_COUNT = 3
KEY_POINTS_MIN_COUNT = 2
KEY_POINT_MAX_CHARS = 28
KEY_POINT_MIN_CHARS = 4

# ---- Fact-check settings ----

STRICT_FACT_MODE = os.getenv("STRICT_FACT_MODE", "1").strip().lower() not in {"0", "false", "no", "off"}
FACT_OVERLAP_MIN = float_env("FACT_OVERLAP_MIN", 0.55, min_value=0.1, max_value=1.0)

# ---- Title validation ----

TITLE_INCOMPLETE_PREFIXES = (
    "获",
    "宣布",
    "发布",
    "推出",
    "进入",
    "回应",
    "跻身",
    "完成",
    "上线",
    "披露",
    "实现",
    "启动",
)

# ---- Second-hand content detection ----

SECOND_HAND_CUES = (
    "据报道",
    "消息称",
    "传闻",
    "网传",
    "爆料",
    "编译",
    "转载",
    "转自",
    "整理自",
    "综合自",
    "rumor",
    "reportedly",
    "according to",
    "via ",
    "source:",
)

DEFAULT_SECOND_HAND_DOMAINS = (
    "qbitai.com",
    "36kr.com",
    "jiemian.com",
    "ifanr.com",
    "techcrunch.com",
    "theverge.com",
    "jiqizhixin.com",
    "zhidx.com",
)

# ---- Quality check weak phrases ----

DETAIL_WEAK_PHRASES = (
    "信息持续跟进",
    "建议查看原文",
    "值得关注",
    "持续观察",
    "后续关注",
)

# ---- Primary source domains ----

DEFAULT_PRIMARY_SOURCE_DOMAINS = (
    "openai.com",
    "anthropic.com",
    "deepseek.com",
    "deepmind.google",
    "mistral.ai",
    "cohere.com",
    "aliyun.com",
    "alibabacloud.com",
    "augmentcode.com",
    "blog.google",
    "ai.meta.com",
    "huggingface.co",
    "runwayml.com",
    "pika.art",
    "luma.ai",
    "lumalabs.ai",
    "stability.ai",
    "elevenlabs.io",
    "suno.com",
    "udio.com",
    "seed.bytedance.com",
    "bytedance.com",
    "tencent.com",
    "hunyuan.tencent.com",
    "moonshot.ai",
    "moonshot.cn",
    "bigmodel.cn",
    "z.ai",
    "minimax.io",
    "arxiv.org",
    "export.arxiv.org",
    "github.com",
)

DEFAULT_PRIMARY_X_HANDLES = (
    "sama",
    "openai",
    "anthropicai",
    "mistralai",
    "deepmind",
    "elonmusk",
    "demishassabis",
    "karpathy",
    "drjimfan",
    "tszzq",
    "goodfellow_ian",
    "codeeditapp",
    "replit",
    "runwayml",
    "elevenlabsio",
)

# ---- AI topic relevance ----

DEFAULT_AI_TOPIC_KEYWORDS = (
    "ai",
    "artificial intelligence",
    "machine learning",
    "deep learning",
    "llm",
    "gpt",
    "chatgpt",
    "rag",
    "agent",
    "agentic",
    "multimodal",
    "diffusion",
    "transformer",
    "inference",
    "fine-tuning",
    "fine tuning",
    "模型",
    "大模型",
    "智能体",
    "多模态",
    "推理",
    "训练",
    "微调",
    "生成式",
    "开源权重",
    "openai",
    "anthropic",
    "deepmind",
    "mistral",
    "qwen",
    "deepseek",
    "hunyuan",
    "moonshot",
    "kimi",
    "gemini",
    "llama",
    "claude",
    "codex",
    "arxiv",
)

# ---- X/Twitter / Nitter hosts ----

X_HOSTS = {
    "x.com",
    "twitter.com",
    "nitter.net",
    "nitter.poast.org",
    "nitter.privacydev.net",
    "nitter.d420.de",
    "nitter.unixfox.eu",
}

# ---- Report parsing patterns ----

REPORT_ITEM_TITLE_PATTERN = re.compile(r"^###\s+\d+[)\.、]\s+(.+)$")
REPORT_ITEM_SOURCE_PATTERN = re.compile(r"^(?:-\s*)?(?:\*{0,2})?(?:来源|source)(?:\*{0,2})\s*[：:](.+)$", flags=re.IGNORECASE)
