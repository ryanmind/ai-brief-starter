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


def path_env(name: str, default: str) -> str:
    """Read a path from environment variable with traversal sanitization.

    Rejects absolute paths and paths containing '..' to prevent path traversal.
    """
    raw = os.getenv(name, default)
    if os.path.isabs(raw) or ".." in raw:
        raise ValueError(f"{name} must be a relative path without traversal, got: {raw}")
    return raw


def float_env(
    name: str, default: float, min_value: float = 0.0, max_value: float = 1.0
) -> float:
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


# ---- Pipeline Control Configuration ----
# 这些参数控制流程行为，主要在 workflow 中覆盖

MAX_ITEMS = int_env("MAX_ITEMS", 120, min_value=10, max_value=500)
TOP_N = int_env("TOP_N", 20, min_value=5, max_value=100)
FETCH_HOURS = int_env("FETCH_HOURS", 24, min_value=1, max_value=168)
PER_SOURCE_ITEMS = int_env("PER_SOURCE_ITEMS", 30, min_value=5, max_value=200)
HISTORY_DEDUP_DAYS = int_env("HISTORY_DEDUP_DAYS", 2, min_value=0, max_value=30)
HISTORY_STATE_MAX_DAYS = int_env(
    "HISTORY_STATE_MAX_DAYS", 14, min_value=1, max_value=90
)
PER_DOMAIN_LIMIT = int_env("PER_DOMAIN_LIMIT", 4, min_value=1, max_value=20)
ARXIV_MAX_ITEMS = int_env("ARXIV_MAX_ITEMS", 4, min_value=0, max_value=20)
TITLE_COMPLETE_RATIO_MIN = float_env(
    "TITLE_COMPLETE_RATIO_MIN", 0.90, min_value=0.5, max_value=1.0
)

# ---- Filter Strictness ----

STRICT_PRIMARY_ONLY = os.getenv("STRICT_PRIMARY_ONLY", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
STRICT_AI_TOPIC_ONLY = os.getenv("STRICT_AI_TOPIC_ONLY", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}

# ---- Quality Check ----

QUALITY_CHECK_STRICT = os.getenv("QUALITY_CHECK_STRICT", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
QUALITY_CHECK_FAIL_OPEN = os.getenv(
    "QUALITY_CHECK_FAIL_OPEN", "1"
).strip().lower() not in {"0", "false", "no", "off"}

# ---- Twitter/X Configuration ----

TWITTERAPI_IO_ENABLED = os.getenv("TWITTERAPI_IO_ENABLED", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
TWITTERAPI_IO_TIMEOUT = int_env("TWITTERAPI_IO_TIMEOUT", 8, min_value=3, max_value=30)
NITTER_RSS_BASES = os.getenv(
    "NITTER_RSS_BASES",
    "https://nitter.net,https://nitter.poast.org,https://nitter.privacydev.net,https://nitter.d420.de,https://nitter.unixfox.eu",
)

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
CONTENT_DEDUPE_MIN_CHARS = int_env(
    "CONTENT_DEDUPE_MIN_CHARS", 18, min_value=8, max_value=80
)

# ---- Fact-check settings ----

STRICT_FACT_MODE = os.getenv("STRICT_FACT_MODE", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
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
    "release",
    "chore",
    "fix",
    "feat",
    "refactor",
    "docs",
    "test",
    "style",
    "build",
    "ci",
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
    "stableaudio.com",
    "elevenlabs.io",
    "suno.com",
    "udio.com",
    "klingai.com",
    "midjourney.com",
    "ideogram.ai",
    "blackforestlabs.ai",
    "leonardo.ai",
    "firefly.adobe.com",
    "cursor.com",
    "windsurf.com",
    "claude.ai",
    "replit.com",
    "aws.amazon.com",
    "tabnine.com",
    "notion.so",
    "grammarly.com",
    "jasper.ai",
    "copy.ai",
    "gamma.app",
    "perplexity.ai",
    "seed.bytedance.com",
    "bytedance.com",
    "tencent.com",
    "hunyuan.tencent.com",
    "moonshot.ai",
    "moonshot.cn",
    "bigmodel.cn",
    "z.ai",
    "minimax.io",
    "hailuoai.com",
    "hailuoai.video",
    "talkie-ai.com",
    "heygen.com",
    "d-id.com",
    "synthesia.io",
    "soulmachines.com",
    "avatarmind.ai",
    "nvidia.com",
    "inworld.ai",
    "character.ai",
    "unity.com",
    "unrealengine.com",
    "liblib.ai",
    "jimeng.jianying.com",
    "yige.baidu.com",
    "arxiv.org",
    "export.arxiv.org",
    "github.com",
    "openclaw.com",
)

DEFAULT_PRIMARY_X_HANDLES = (
    # AI 创始人/大佬
    "sama",
    "elonmusk",
    "demishassabis",
    "anthropicai",
    "mistralai",
    "karpathy",
    "ilyasut",
    "drjimfan",
    "goodfellow_ian",
    "ylecun",
    "andrewyng",
    "nvidia",
    # 中国 AI 领军人物
    "tszzq",
    "kaifulee",
    "ictclp",
    # 官方账号
    "openai",
    "deepmind",
    "googledeepmind",
    "minimax_ai",
    "minimaxagent",
    "hailuo_ai",
    "minimax_aiagent",
    # 代码/视频/音频工具
    "codeeditapp",
    "githubcopilot",
    "codeiumdev",
    "replit",
    "runwayml",
    "pika_labs",
    "lumalabsai",
    "stabilityai",
    "midjourney",
    "ideogram_ai",
    "blklabsai",
    "leonardoai_",
    "adobefirefly",
    "suno_ai_",
    "udiomusic",
    "elevenlabsio",
    "metaai",
    "awscloud",
    "tabnine",
    "notionhq",
    "grammarly",
    "jasper_ai",
    "copy_ai",
    "gammaapp",
    "perplexity_ai",
    "heygen_official",
    "d_id_ai",
    "synthesiaav",
    "soul_machines",
    "openclaw",
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
    "github trending",
    "open source",
    "开源项目",
    "openclaw",
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

# ---- GitHub Trending ----
# GITHUB_TOKEN 可选，用于提高 GitHub API 速率限制

GITHUB_API_TIMEOUT = int_env("GITHUB_API_TIMEOUT", 10, min_value=5, max_value=30)

# ---- Pipeline Optimization Configuration ----
# 启用优化管线（合并LLM调用，智能审核）
USE_OPTIMIZED_PIPELINE = os.getenv(
    "USE_OPTIMIZED_PIPELINE", "1"
).strip().lower() not in {"0", "false", "no", "off"}

# ---- LLM API Configuration ----
# Use LLM_PROVIDER environment variable to select provider:
# - "openai-compat" (default): OpenAI-compatible API (works with Qwen, OpenAI, Iflow, etc.)
# Add new provider implementations in src/llm/providers/

LLM_API_KEY_ENV = "LLM_API_KEY"  # 环境变量名
LLM_MODEL_DEFAULT = "MiniMax-M2.7"  # 默认模型
LLM_BASE_URL = "https://api.minimaxi.com/anthropic"  # API 端点

# ---- LLM Failover Configuration ----
# 备用模型列表，主模型失败时按顺序尝试（逗号分隔）
# 例如: "qwen3-coder,qwen2-72b-instruct,gpt-4o-mini


def get_fallback_llm_models() -> list[str]:
    """获取故障转移备用模型列表。"""
    raw = os.getenv("FALLBACK_LLM_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return []


# ---- Multi-Model Review Configuration ----
# 多模型审核配置：用多个模型交叉验证生成结果的真实性

REVIEW_MODELS_DEFAULT = (LLM_MODEL_DEFAULT,)
REVIEW_ENABLED = os.getenv("REVIEW_ENABLED", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
REVIEW_PASS_THRESHOLD = int_env(
    "REVIEW_PASS_THRESHOLD", 1, min_value=1, max_value=5
)  # 至少几个模型通过

# ---- LLM Cache Configuration ----
# LLM 响应缓存配置：避免重复调用相同请求，降低 token 消耗

LLM_CACHE_ENABLED = os.getenv("LLM_CACHE_ENABLED", "1").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
LLM_CACHE_TTL = int_env(
    "LLM_CACHE_TTL", 86400 * 7, min_value=3600, max_value=86400 * 30
)  # 缓存过期时间（秒），默认7天
LLM_CACHE_PATH = path_env("LLM_CACHE_PATH", "cache/llm_cache.json")  # 缓存文件路径


def get_review_models() -> list[str]:
    """获取用于审核的模型列表。"""
    raw = os.getenv("REVIEW_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return list(REVIEW_MODELS_DEFAULT)


# LLM 辅助函数
def get_llm_api_key() -> str:
    """获取 LLM API Key，未设置时抛出异常。"""
    key = os.getenv(LLM_API_KEY_ENV, "").strip()
    if not key:
        raise RuntimeError(f"{LLM_API_KEY_ENV} 未设置")
    return key


def get_llm_model() -> str:
    """获取 LLM 模型名称。"""
    return os.getenv("LLM_MODEL", LLM_MODEL_DEFAULT).strip() or LLM_MODEL_DEFAULT


# ---- Report parsing patterns ----

REPORT_ITEM_TITLE_PATTERN = re.compile(r"^###\s+\d+[)\.、]\s+(.+)$")
REPORT_ITEM_SOURCE_PATTERN = re.compile(
    r"^(?:-\s*)?(?:\*{0,2})?(?:来源|source)(?:\*{0,2})\s*[：:](.+)$",
    flags=re.IGNORECASE,
)
