"""Markdown report rendering, category balance checking, and quality gate."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.config import X_HOSTS
from src.text_utils import (
    clean_generated_text,
    ensure_sentence_end,
    host_matches,
    is_placeholder_text,
    nitter_to_x_url,
    normalize_host,
    normalize_key_points,
    shorten_for_highlight,
)

logger = logging.getLogger(__name__)


SOURCE_CATEGORY_DOMAINS: dict[str, set[str]] = {
    "vendor": {
        "openai.com", "anthropic.com", "deepseek.com", "deepmind.google", "mistral.ai",
        "cohere.com", "ai.meta.com", "stability.ai", "runwayml.com", "elevenlabs.io",
        "suno.com", "pika.art", "luma.ai", "lumalabs.ai", "udio.com",
        "seed.bytedance.com", "bytedance.com", "tencent.com", "hunyuan.tencent.com",
        "moonshot.ai", "moonshot.cn", "bigmodel.cn", "minimax.io",
        "aliyun.com", "alibabacloud.com", "augmentcode.com",
    },
    "academic": {"arxiv.org", "export.arxiv.org"},
    "social": X_HOSTS,
    "github": {"github.com"},
}


def check_category_balance(items: list[dict[str, str]]) -> dict[str, int]:
    """统计各类来源分布并输出告警。"""
    counts: dict[str, int] = {cat: 0 for cat in SOURCE_CATEGORY_DOMAINS}
    counts["other"] = 0
    for item in items:
        host = normalize_host(urlparse(item.get("link", "")).netloc or "")
        matched = False
        for cat, domains in SOURCE_CATEGORY_DOMAINS.items():
            if host_matches(host, domains):
                counts[cat] += 1
                matched = True
                break
        if not matched:
            counts["other"] += 1

    logger.info("category balance: %s", json.dumps(counts, ensure_ascii=False))
    total = len(items)
    if total > 0:
        for cat, count in counts.items():
            if count / total >= 0.7 and total >= 5:
                logger.warning(
                    "category '%s' dominates report (%d/%d = %.0f%%), content diversity may be low",
                    cat, count, total, count / total * 100,
                )
    if counts.get("vendor", 0) == 0 and total > 0:
        logger.warning("no vendor news in final report, consider checking source availability")
    return counts


def render_markdown(items: list[dict[str, str]]) -> str:
    now = datetime.now()
    today_cn = now.strftime("%Y年%m月%d日%H:%M:%S")
    lines = [
        f"## \U0001f4f0 AI 早报 · {today_cn}",
        "",
        "### \U0001f4cc 本期摘要",
    ]

    for idx, item in enumerate(items[:5], 1):
        title = clean_generated_text(item.get("title", ""))
        brief = shorten_for_highlight(clean_generated_text(item.get("brief", "")))
        if not title and not brief:
            continue
        if title and brief:
            lines.append(f"- {idx}. {title}：{ensure_sentence_end(brief)}")
        elif brief:
            lines.append(f"- {idx}. {ensure_sentence_end(brief)}")
        else:
            lines.append(f"- {idx}. {title}")

    lines.append("")
    for idx, item in enumerate(items, 1):
        if idx > 1:
            lines.append("")
        brief = ensure_sentence_end(clean_generated_text(item.get("brief", "")))
        impact = ensure_sentence_end(clean_generated_text(item.get("impact", "")))
        title = clean_generated_text(item.get("title", ""))
        source = nitter_to_x_url((item.get("link", "") or "").strip())
        key_points: list[str] = []
        for point in normalize_key_points(item.get("key_points")):
            cleaned_point = clean_generated_text(point)
            if not cleaned_point or is_placeholder_text(cleaned_point):
                continue
            if re.match(r"^(?:关键点|要点)\s*[：:]", cleaned_point):
                continue
            key_points.append(cleaned_point)

        entry_lines = [f"### {idx}. {title or '未命名条目'}"]
        if brief:
            entry_lines.append(f"**摘要**：{brief}")
        if key_points:
            entry_lines.append("**关键点**")
            entry_lines.extend([f"- {point}" for point in key_points])
        if impact:
            entry_lines.append(f"**影响分析**：{impact}")
        if source:
            entry_lines.append(f"**来源**：[原文链接]({source})")
        while entry_lines and not entry_lines[-1].strip():
            entry_lines.pop()
        lines.extend(entry_lines)
    return "\n".join(lines)


def prepend_quality_review_banner(markdown: str) -> str:
    if not markdown.strip():
        return markdown
    if "质量提示：本期内容在自动质检中发现缺陷" in markdown:
        return markdown

    lines = markdown.splitlines()
    insert_at = 1 if lines and lines[0].startswith("# ") else 0
    banner_lines = [
        "> \u26a0\ufe0f 质量提示：本期内容在自动质检中发现缺陷，已按不断流策略发布，请优先人工复核。",
        "> 详情请查看 `reports/quality_metrics.json` 与 `reports/high_risk_items.md`。",
        "",
    ]
    merged = lines[:insert_at] + [""] + banner_lines + lines[insert_at:]
    return "\n".join(merged).rstrip() + "\n"


def run_quality_checks(
    path: Path,
    autofix: bool = False,
    metrics_output: Path | None = None,
    high_risk_output: Path | None = None,
) -> int:
    """Wrapper around scripts/report_quality_check.py."""
    try:
        from scripts.report_quality_check import run_checks
    except ImportError:
        logger.warning("quality check module not found, skipping checks")
        return 0

    return run_checks(
        path=str(path),
        autofix=autofix,
        metrics_output=str(metrics_output) if metrics_output else None,
        high_risk_output=str(high_risk_output) if high_risk_output else None,
    )
