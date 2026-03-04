"""LLM interaction utilities: chat, JSON extraction, ranking, localization."""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

from openai import OpenAI

from src.config import (
    BRIEF_MAX_CHARS,
    DETAIL_MAX_CHARS,
    IMPACT_MAX_CHARS,
    KEY_POINT_MAX_CHARS,
    KEY_POINTS_MAX_COUNT,
    TITLE_MAX_CHARS,
    int_env,
    parse_csv_env,
    DEFAULT_AI_TOPIC_KEYWORDS,
)
from src.text_utils import (
    build_default_key_points,
    build_fallback_impact,
    build_subject_guaranteed_title,
    clean_text,
    finalize_key_points,
    fix_items_detail,
    is_placeholder_text,
    item_dedupe_fingerprints,
    normalize_key_points,
    pick_preferred_title,
    strip_markdown_fence,
    polish_result_is_safe,
)

logger = logging.getLogger(__name__)


def llm_chat(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int | None = None,
    max_retries: int = 3,
) -> str:
    params: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    if max_tokens is not None and max_tokens > 0:
        params["max_tokens"] = max_tokens

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(**params)
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            last_error = exc
            if attempt == max_retries - 1:
                logger.warning(
                    "llm_chat: failed after %d attempts: %s",
                    max_retries,
                    exc,
                )
                raise
            wait = 2**attempt
            logger.warning(
                "llm_chat: retry %d/%d after %ds: %s",
                attempt + 1,
                max_retries,
                wait,
                exc,
            )
            time.sleep(wait)

    # This line is theoretically unreachable because the loop either returns or raises,
    # but keeps type-checkers happy.
    if last_error is not None:
        raise last_error
    raise RuntimeError("llm_chat failed without raising an exception")


def extract_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    candidates: list[str] = [raw]

    if raw.startswith("```"):
        fence_stripped = re.sub(r"^```(?:json)?", "", raw).strip()
        fence_stripped = re.sub(r"```$", "", fence_stripped).strip()
        candidates.append(fence_stripped)

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(raw[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("model output is not valid JSON object")


def fallback_selection(items: list[dict[str, str]], top_n: int, start_score: int = 100) -> list[dict[str, str]]:
    fallback: list[dict[str, str]] = []
    for idx, item in enumerate(items[:top_n], 1):
        result = item.copy()
        result["score"] = str(max(start_score - idx + 1, 0))

        summary = clean_text(item.get("summary", ""))
        if summary:
            result["brief"] = summary[:BRIEF_MAX_CHARS]
        else:
            result["brief"] = clean_text(item.get("title", ""))[:BRIEF_MAX_CHARS]

        result["details"] = summary[:DETAIL_MAX_CHARS] if summary else result["brief"]
        result["impact"] = build_fallback_impact(result)
        result["key_points"] = build_default_key_points(result)
        result["title"] = build_subject_guaranteed_title(
            title=result.get("title", ""),
            summary=result.get("summary", ""),
            link=result.get("link", ""),
        )
        fallback.append(result)
    return fallback


def backfill_selected_items(
    selected: list[dict[str, str]],
    items: list[dict[str, str]],
    top_n: int,
) -> list[dict[str, str]]:
    target_count = min(top_n, len(items))
    if len(selected) >= target_count:
        return selected[:target_count]

    used_fingerprints: set[str] = set()
    for item in selected:
        used_fingerprints.update(item_dedupe_fingerprints(item))

    remaining: list[dict[str, str]] = []
    for item in items:
        fingerprints = item_dedupe_fingerprints(item)
        if fingerprints and used_fingerprints.intersection(fingerprints):
            continue
        used_fingerprints.update(fingerprints)
        remaining.append(item)

    needed = target_count - len(selected)
    if needed <= 0:
        return selected[:target_count]

    last_score = 100
    if selected:
        try:
            last_score = int(selected[-1].get("score", "100"))
        except (TypeError, ValueError):
            last_score = 100

    selected.extend(fallback_selection(remaining, top_n=needed, start_score=max(last_score - 1, 0)))
    return selected[:target_count]


def rank_and_summarize(
    items: list[dict[str, str]],
    qwen_api_key: str,
    qwen_model: str,
    top_n: int = 20,
) -> list[dict[str, str]]:
    client = OpenAI(api_key=qwen_api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

    candidates: list[str] = []
    for idx, item in enumerate(items, 1):
        candidates.append(
            (
                f"{idx}. 标题: {item['title']}\n"
                f"链接: {item['link']}\n"
                f"内容: {item['summary'][:350]}\n"
                f"发布时间: {item['published']}\n"
            )
        )

    user_prompt = (
        "你是AI资讯编辑。请从候选中选出最值得做早报的内容并摘要。\n"
        "严格输出JSON："
        '{"items":[{"id":1,"score":90,"title":"...","brief":"...","details":"...","impact":"...","key_points":["...","..."]}]}\n'
        f"最多返回{top_n}条；title<={TITLE_MAX_CHARS}字；brief<={BRIEF_MAX_CHARS}字；details<={DETAIL_MAX_CHARS}字；impact<={IMPACT_MAX_CHARS}字；必须基于输入，不编造；"
        "brief和impact必须使用简体中文。"
        "details写1-2句具体事实，尽量包含实体名/数字/版本/时间等可核实信息。"
        f"key_points返回2-3条，每条<={KEY_POINT_MAX_CHARS}字。"
        "标题必须完整，包含主体名称（公司/产品/人物），不能省略主语。"
        "若出现版本号，标题必须明确“哪个产品/仓库的哪个版本”，禁止仅写“release:4.6.3”或“5.4即将上线”。"
        "写法要可直接用于朋友圈/公众号：先结论后细节、避免空话与套话。"
        "brief只写1句，尽量包含“主体+动作+结果”；impact回答“为什么值得关注”。"
        "仅可选择一手来源（官方公告、论文原文、作者/机构本人账号原帖），"
        "禁止媒体转述、二手解读、汇总搬运、未证实传闻。\n\n"
        + "\n".join(candidates)
    )

    last_error: Exception | None = None
    data: dict[str, Any] | None = None
    for attempt in range(2):
        system_prompt = "你是严谨的科技新闻编辑，只输出JSON。"
        if attempt > 0:
            system_prompt = (
                "你是严谨的科技新闻编辑。"
                "你上一次输出格式错误，这次必须仅输出一个合法JSON对象，不要输出任何说明文字。"
            )

        try:
            raw = llm_chat(
                client=client,
                model=qwen_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            data = extract_json(raw)
            break
        except ValueError as exc:
            last_error = exc
        except Exception as exc:
            last_error = exc
            logger.warning("rank_and_summarize: LLM request failed on attempt %d: %s", attempt + 1, exc)

    if data is None:
        logger.warning("rank_and_summarize: 模型输出无法解析，使用 fallback。error=%s", last_error)
        return fallback_selection(items=items, top_n=top_n)

    selected: list[dict[str, str]] = []
    used_item_ids: set[int] = set()
    selected_fingerprints: set[str] = set()
    rows = data.get("items", [])
    if not isinstance(rows, list):
        logger.warning("rank_and_summarize: items 字段不是列表，使用 fallback。")
        return fallback_selection(items=items, top_n=top_n)

    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            idx = int(row.get("id", 0))
        except (TypeError, ValueError):
            continue
        if idx < 1 or idx > len(items):
            continue
        if idx in used_item_ids:
            continue
        result = items[idx - 1].copy()
        try:
            score = int(row.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        result["score"] = str(score)
        title = pick_preferred_title(str(row.get("title", "")), result.get("title", ""))
        if title:
            if title != clean_text(str(row.get("title", "")))[:TITLE_MAX_CHARS]:
                logger.info("rank_and_summarize: 标题疑似缺主语，回退为原始标题。")
            result["title"] = build_subject_guaranteed_title(
                title=title,
                summary=result.get("summary", ""),
                link=result.get("link", ""),
            )
        result["brief"] = clean_text(str(row.get("brief", "")))[:BRIEF_MAX_CHARS]
        details = clean_text(str(row.get("details", "")))[:DETAIL_MAX_CHARS]
        if not details:
            details = clean_text(result.get("summary", ""))[:DETAIL_MAX_CHARS]
        if not details:
            details = result["brief"]
        result["details"] = details
        impact = clean_text(str(row.get("impact", "")))[:IMPACT_MAX_CHARS]
        if not impact or "建议查看原文" in impact or "信息持续跟进" in impact:
            impact = build_fallback_impact(result)
        result["impact"] = impact
        result["key_points"] = finalize_key_points(normalize_key_points(row.get("key_points")), result)
        fingerprints = item_dedupe_fingerprints(result)
        if fingerprints and selected_fingerprints.intersection(fingerprints):
            continue
        selected_fingerprints.update(fingerprints)
        used_item_ids.add(idx)
        selected.append(result)

    selected.sort(key=lambda x: int(x.get("score", "0")), reverse=True)
    if not selected:
        logger.warning("rank_and_summarize: 解析结果为空，使用 fallback。")
        return fallback_selection(items=items, top_n=top_n)
    selected = backfill_selected_items(selected=selected, items=items, top_n=top_n)
    selected.sort(key=lambda x: int(x.get("score", "0")), reverse=True)
    selected = selected[: min(top_n, len(items))]
    return fix_items_detail(selected)


def localize_items_to_chinese(
    items: list[dict[str, str]],
    qwen_api_key: str,
    qwen_model: str,
) -> list[dict[str, str]]:
    if not items:
        return items

    client = OpenAI(api_key=qwen_api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    payload = [
        {
            "id": idx + 1,
            "title": item.get("title", ""),
            "brief": item.get("brief", ""),
            "details": item.get("details", ""),
            "impact": item.get("impact", ""),
            "key_points": item.get("key_points", [])[:KEY_POINTS_MAX_COUNT],
            "source_link": item.get("link", ""),
        }
        for idx, item in enumerate(items)
    ]

    user_prompt = (
        "请把下面资讯字段统一改写为简体中文，并完成数据清洗，必须保持事实不变。\n"
        "严格输出JSON："
        '{"items":[{"id":1,"title":"中文标题","brief":"中文摘要","details":"中文细节","impact":"中文影响","key_points":["要点1","要点2"]}]}\n'
        f"要求：title<={TITLE_MAX_CHARS}字，brief<={BRIEF_MAX_CHARS}字，details<={DETAIL_MAX_CHARS}字，impact<={IMPACT_MAX_CHARS}字，"
        f"key_points最多{KEY_POINTS_MAX_COUNT}条且每条<={KEY_POINT_MAX_CHARS}字。\n\n"
        "清洗规则：删除占位词（如 value/null/none/n-a）、无意义噪声字符（如孤立 @、重复标点）、"
        "空洞重复短语与无信息量内容；若字段无法清洗出有效信息则返回空字符串。\n\n"
        "标题规则：标题必须包含明确主体；若含版本号，需明确产品/仓库名称，禁止仅保留“release:4.6.3”这类低信息标题。\n\n"
        "文风要求：口语化但专业，信息密度高，像可直接发朋友圈/公众号的成稿。"
        "避免机械重复开头（如连续使用“宣布/发布”）。\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    try:
        raw = llm_chat(
            client=client,
            model=qwen_model,
            system_prompt="你是中文科技编辑，只输出合法JSON。",
            user_prompt=user_prompt,
        )
        data = extract_json(raw)
    except Exception as exc:
        logger.warning("localize_items_to_chinese: 本地化失败，回退原文。error=%s", exc)
        return items

    rows = data.get("items", [])
    if not isinstance(rows, list):
        return items

    id_to_row: dict[int, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            idx = int(row.get("id", 0))
        except (TypeError, ValueError):
            continue
        if 1 <= idx <= len(items):
            id_to_row[idx] = row

    localized: list[dict[str, str]] = []
    for idx, item in enumerate(items, 1):
        row = id_to_row.get(idx)
        if row is None:
            localized.append(item)
            continue

        merged = item.copy()
        title_cn = clean_text(str(row.get("title", "")))[:TITLE_MAX_CHARS]
        brief_cn = clean_text(str(row.get("brief", "")))[:BRIEF_MAX_CHARS]
        details_cn = clean_text(str(row.get("details", "")))[:DETAIL_MAX_CHARS]
        impact_cn = clean_text(str(row.get("impact", "")))[:IMPACT_MAX_CHARS]

        if is_placeholder_text(title_cn):
            title_cn = ""
        if is_placeholder_text(brief_cn):
            brief_cn = ""
        if is_placeholder_text(details_cn):
            details_cn = ""
        if is_placeholder_text(impact_cn):
            impact_cn = ""

        if title_cn:
            merged["title"] = build_subject_guaranteed_title(
                title=title_cn,
                summary=merged.get("summary", ""),
                link=merged.get("link", ""),
            )
        if brief_cn:
            merged["brief"] = brief_cn
        if details_cn:
            merged["details"] = details_cn
        if impact_cn:
            merged["impact"] = impact_cn
        merged["key_points"] = finalize_key_points(normalize_key_points(row.get("key_points")), merged)
        localized.append(merged)

    missed = len(items) - len(id_to_row)
    if missed > 0:
        logger.warning("localize_items_to_chinese: %d/%d 条未被本地化，保留原文。", missed, len(items))
    return fix_items_detail(localized)


def enforce_titles_with_subject(
    items: list[dict[str, str]],
    qwen_api_key: str,
    qwen_model: str,
) -> list[dict[str, str]]:
    if not items:
        return items

    payload = [
        {
            "id": idx + 1,
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "source_link": item.get("link", ""),
        }
        for idx, item in enumerate(items)
    ]

    rewritten_titles: dict[int, str] = {}
    try:
        client = OpenAI(api_key=qwen_api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
        user_prompt = (
            "你是AI资讯标题编辑。请重写每条标题，要求：\n"
            "1) 每一条标题都必须包含明确主语（公司/产品/机构/账号）。\n"
            "2) 若包含版本号，必须写清“谁的什么版本”，禁止无主语标题。\n"
            "3) 保持事实不变，标题简洁，长度不超过40字。\n"
            "严格输出JSON："
            '{"items":[{"id":1,"title":"含明确主语的新标题"}]}\n\n'
            + json.dumps(payload, ensure_ascii=False)
        )
        raw = llm_chat(
            client=client,
            model=qwen_model,
            system_prompt="你是严谨的中文标题编辑，只输出合法JSON。",
            user_prompt=user_prompt,
        )
        data = extract_json(raw)
        rows = data.get("items", [])
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                try:
                    row_id = int(row.get("id", 0))
                except (TypeError, ValueError):
                    continue
                if row_id < 1 or row_id > len(items):
                    continue
                rewritten = clean_text(str(row.get("title", "")))[:TITLE_MAX_CHARS]
                if rewritten:
                    rewritten_titles[row_id] = rewritten
    except Exception as exc:
        logger.warning("enforce_titles_with_subject: llm rewrite failed, fallback to deterministic repair. error=%s", exc)

    normalized: list[dict[str, str]] = []
    for idx, item in enumerate(items, 1):
        merged = item.copy()
        title_candidate = rewritten_titles.get(idx, merged.get("title", ""))
        merged["title"] = build_subject_guaranteed_title(
            title=title_candidate,
            summary=merged.get("summary", ""),
            link=merged.get("link", ""),
        )
        normalized.append(merged)
    return normalized


def classify_ai_topic_items_with_llm(
    items: list[dict[str, str]],
    qwen_api_key: str,
    qwen_model: str,
    keywords: set[str],
) -> tuple[list[bool | None], dict[str, int]]:
    batch_size = int_env("AI_TOPIC_LLM_BATCH_SIZE", 24, min_value=1, max_value=80)
    client = OpenAI(api_key=qwen_api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    decisions: list[bool | None] = [None] * len(items)
    stats: dict[str, int] = {}
    keywords_hint = "、".join(sorted(keywords)) if keywords else "无"

    for batch_start in range(0, len(items), batch_size):
        batch = items[batch_start : batch_start + batch_size]
        payload: list[dict[str, Any]] = []
        for idx, item in enumerate(batch, 1):
            payload.append(
                {
                    "id": idx,
                    "title": clean_text(item.get("title", ""))[:TITLE_MAX_CHARS],
                    "summary": clean_text(item.get("summary", ""))[:360],
                    "link": item.get("link", ""),
                }
            )

        user_prompt = (
            "你是AI资讯审核编辑。请判断每条是否属于“AI相关内容”。\n"
            "判定为 true 的条件：与AI模型/算法/论文/智能体/推理/训练/AI产品发布/AI基础设施直接相关。\n"
            "判定为 false 的条件：社会新闻、泛政治评论、纯商业活动、无AI实质信息的内容。\n"
            "严格输出JSON："
            '{"items":[{"id":1,"is_ai_topic":true,"reason":"一句话理由"}]}\n'
            "id 必须对应输入；禁止输出任何额外说明。\n"
            f"可参考关键词（仅作辅助，不是硬规则）：{keywords_hint}\n\n"
            + json.dumps(payload, ensure_ascii=False)
        )

        try:
            raw = llm_chat(
                client=client,
                model=qwen_model,
                system_prompt="你是严谨的信息审核员，只输出合法JSON。",
                user_prompt=user_prompt,
            )
            data = extract_json(raw)
        except Exception as exc:
            stats["llm_batch_failed_kept"] = stats.get("llm_batch_failed_kept", 0) + len(batch)
            logger.warning(
                "ai-topic llm batch failed, keep batch as fallback. start=%s size=%s error=%s",
                batch_start,
                len(batch),
                exc,
            )
            continue

        rows = data.get("items", [])
        if not isinstance(rows, list):
            stats["llm_batch_invalid_kept"] = stats.get("llm_batch_invalid_kept", 0) + len(batch)
            logger.warning(
                "ai-topic llm batch invalid payload, keep batch as fallback. start=%s size=%s",
                batch_start,
                len(batch),
            )
            continue

        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                row_id = int(row.get("id", 0))
            except (TypeError, ValueError):
                continue
            if row_id < 1 or row_id > len(batch):
                continue

            decision_raw = row.get("is_ai_topic")
            decision: bool | None = None
            if isinstance(decision_raw, bool):
                decision = decision_raw
            elif isinstance(decision_raw, str):
                lowered = decision_raw.strip().lower()
                if lowered in {"true", "yes", "1", "ai", "related"}:
                    decision = True
                elif lowered in {"false", "no", "0", "not_ai", "non_ai"}:
                    decision = False
            if decision is None:
                continue
            decisions[batch_start + row_id - 1] = decision

    unclassified = sum(1 for value in decisions if value is None)
    if unclassified > 0:
        stats["llm_unclassified_kept"] = unclassified
    return decisions, stats


def polish_markdown_with_llm(markdown: str, qwen_api_key: str, qwen_model: str) -> str:
    enabled = os.getenv("FINAL_POLISH_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
    if not enabled:
        return markdown

    source_markdown = str(markdown or "").strip()
    if not source_markdown:
        return markdown

    client = OpenAI(api_key=qwen_api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    user_prompt = (
        "请只做文案润色，提升可读性；必须保持 Markdown 结构、标题层级、编号、链接和数字不变。\n"
        "硬性约束：\n"
        "1) 不得新增或删除任何条目；\n"
        "2) 所有 URL 必须原样保留；\n"
        "3) 所有数字（含百分比/版本号）必须原样保留；\n"
        "4) 字段标签“摘要/关键点/影响分析/来源”保持不变；\n"
        "5) 仅输出润色后的完整 Markdown 正文，不要解释，不要代码块。\n\n"
        + source_markdown
    )

    try:
        polished = llm_chat(
            client=client,
            model=qwen_model,
            system_prompt="你是严谨的中文科技编辑，只做润色改写，不改事实与结构。",
            user_prompt=user_prompt,
        )
    except Exception as exc:
        logger.warning("polish_markdown_with_llm: LLM request failed, keep original markdown. error=%s", exc)
        return markdown

    polished = strip_markdown_fence(polished)
    if not polished:
        return markdown
    if polish_result_is_safe(source_markdown, polished):
        return polished

    logger.warning("polish_markdown_with_llm: guard rejected polished markdown, keep original")
    return markdown
