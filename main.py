from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import feedparser
from dateutil import parser as dtparser
from openai import OpenAI

BRIEF_MAX_CHARS = 120
IMPACT_MAX_CHARS = 100
TITLE_MAX_CHARS = 50
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
DEFAULT_PRIMARY_SOURCE_DOMAINS = (
    "openai.com",
    "anthropic.com",
    "deepseek.com",
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
    "elonmusk",
    "demishassabis",
    "karpathy",
    "drjimfan",
    "runwayml",
    "elevenlabsio",
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

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_time(entry: Any) -> Optional[datetime]:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            dt = dtparser.parse(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def normalize_host(host: str) -> str:
    normalized = host.strip().lower()
    if normalized.startswith("www."):
        normalized = normalized[4:]
    return normalized


def parse_csv_env(name: str, default_values: tuple[str, ...]) -> set[str]:
    raw = os.getenv(name)
    values = raw.split(",") if raw is not None else list(default_values)
    return {value.strip().lower() for value in values if value.strip()}


def host_matches(host: str, allowed_domains: set[str]) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains)


def extract_account_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return ""
    return path.split("/", 1)[0].strip().lower()


def contains_second_hand_cue(text: str) -> bool:
    normalized = text.lower()
    return any(cue in normalized for cue in SECOND_HAND_CUES)


def contains_second_hand_domain(text: str, blocked_domains: set[str]) -> bool:
    normalized = text.lower()
    return any(domain in normalized for domain in blocked_domains)


def get_primary_rejection_reason(
    item: dict[str, str],
    allowed_domains: set[str],
    allowed_x_handles: set[str],
    blocked_domains: set[str] | None = None,
) -> str | None:
    link = (item.get("link", "") or "").strip()
    if not link:
        return "missing_link"

    parsed = urlparse(link)
    host = normalize_host(parsed.netloc or "")
    if not host:
        return "missing_host"

    x_hosts = {"x.com", "twitter.com", "nitter.net", "nitter.poast.org", "nitter.privacydev.net"}
    if host in x_hosts:
        account = extract_account_from_url(link)
        if not account:
            return "missing_x_account"
        if allowed_x_handles and account not in allowed_x_handles:
            return "non_primary_x_handle"
    else:
        if not host_matches(host, allowed_domains):
            return "non_primary_domain"

    evidence = f"{clean_text(item.get('title', ''))} {clean_text(item.get('summary', ''))}".strip()
    if evidence and contains_second_hand_cue(evidence):
        return "second_hand_cue"

    if blocked_domains is None:
        blocked_domains = parse_csv_env("SECOND_HAND_DOMAINS", DEFAULT_SECOND_HAND_DOMAINS)
    if evidence and contains_second_hand_domain(evidence, blocked_domains):
        return "second_hand_domain"

    return None


def is_primary_item(
    item: dict[str, str],
    allowed_domains: set[str],
    allowed_x_handles: set[str],
) -> bool:
    return get_primary_rejection_reason(
        item=item,
        allowed_domains=allowed_domains,
        allowed_x_handles=allowed_x_handles,
    ) is None


def filter_primary_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    filtered, _ = filter_primary_items_with_stats(items)
    return filtered


def filter_primary_items_with_stats(items: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
    strict_primary_only = os.getenv("STRICT_PRIMARY_ONLY", "1").strip().lower()
    if strict_primary_only in {"0", "false", "no", "off"}:
        return items, {"strict_mode_disabled": len(items)}

    allowed_domains = parse_csv_env("PRIMARY_SOURCE_DOMAINS", DEFAULT_PRIMARY_SOURCE_DOMAINS)
    allowed_x_handles = parse_csv_env("PRIMARY_X_HANDLES", DEFAULT_PRIMARY_X_HANDLES)
    blocked_domains = parse_csv_env("SECOND_HAND_DOMAINS", DEFAULT_SECOND_HAND_DOMAINS)
    filtered: list[dict[str, str]] = []
    rejected_stats: dict[str, int] = {}

    for item in items:
        reason = get_primary_rejection_reason(
            item=item,
            allowed_domains=allowed_domains,
            allowed_x_handles=allowed_x_handles,
            blocked_domains=blocked_domains,
        )
        if reason is None:
            filtered.append(item)
            continue
        rejected_stats[reason] = rejected_stats.get(reason, 0) + 1

    return filtered, rejected_stats


def load_sources(path: str = "sources.txt") -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    raw_sources = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    expanded: list[str] = []
    for source in raw_sources:
        expanded.extend(expand_source_urls(source))
    return list(dict.fromkeys(expanded))


def expand_source_urls(source: str) -> list[str]:
    parsed = urlparse(source)
    host = (parsed.netloc or "").lower()

    if host in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        path = (parsed.path or "").strip("/")
        handle = path.split("/", 1)[0] if path else ""
        reserved = {"home", "explore", "search", "i", "messages", "notifications", "settings"}
        if handle and handle not in reserved:
            raw_bases = os.getenv(
                "NITTER_RSS_BASES",
                "https://nitter.net,https://nitter.poast.org,https://nitter.privacydev.net",
            )
            bases = [base.strip().rstrip("/") for base in raw_bases.split(",") if base.strip()]
            return [f"{base}/{handle}/rss" for base in dict.fromkeys(bases)]

    return [source]


def fetch_items(sources: list[str], hours: int = 36, per_source: int = 30) -> list[dict[str, str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    for source in sources:
        feed = feedparser.parse(source)
        entries = getattr(feed, "entries", [])
        for entry in entries[:per_source]:
            title = clean_text(entry.get("title", ""))
            link = (entry.get("link", "") or "").split("#")[0]
            summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
            published = parse_time(entry)

            if not title or not link:
                continue
            if published and published < cutoff:
                continue

            key = hashlib.md5((link.split("?")[0] + "|" + title.lower()).encode("utf-8")).hexdigest()
            if key in seen:
                continue
            seen.add(key)

            items.append(
                {
                    "title": title[:200],
                    "link": link,
                    "summary": summary[:1000],
                    "published": published.isoformat() if published else "",
                }
            )

    items.sort(key=lambda x: x.get("published", ""), reverse=True)
    return items


def llm_chat(client: OpenAI, model: str, system_prompt: str, user_prompt: str, max_tokens: int = 2200) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


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


def fallback_selection(items: list[dict[str, str]], top_n: int) -> list[dict[str, str]]:
    fallback: list[dict[str, str]] = []
    for idx, item in enumerate(items[:top_n], 1):
        result = item.copy()
        result["score"] = str(100 - idx)

        summary = clean_text(item.get("summary", ""))
        if summary:
            result["brief"] = summary[:BRIEF_MAX_CHARS]
        else:
            result["brief"] = clean_text(item.get("title", ""))[:BRIEF_MAX_CHARS]

        result["impact"] = "信息持续跟进中，建议查看原文链接。"
        fallback.append(result)
    return fallback


def rank_and_summarize(
    items: list[dict[str, str]],
    qwen_api_key: str,
    qwen_model: str,
    top_n: int = 10,
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
        '{"items":[{"id":1,"score":90,"title":"...","brief":"...","impact":"..."}]}\n'
        f"最多返回{top_n}条；title<={TITLE_MAX_CHARS}字；brief<={BRIEF_MAX_CHARS}字；impact<={IMPACT_MAX_CHARS}字；必须基于输入，不编造；"
        "brief和impact必须使用简体中文。"
        "标题必须完整，包含主体名称（公司/产品/人物），不能省略主语。"
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

        raw = llm_chat(
            client=client,
            model=qwen_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        try:
            data = extract_json(raw)
            break
        except ValueError as exc:
            last_error = exc

    if data is None:
        logger.warning("rank_and_summarize: 模型输出无法解析，使用 fallback。error=%s", last_error)
        return fallback_selection(items=items, top_n=top_n)

    selected: list[dict[str, str]] = []
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
        result = items[idx - 1].copy()
        try:
            score = int(row.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        result["score"] = str(score)
        title = clean_text(str(row.get("title", "")))[:TITLE_MAX_CHARS]
        if title:
            result["title"] = title
        result["brief"] = clean_text(str(row.get("brief", "")))[:BRIEF_MAX_CHARS]
        result["impact"] = clean_text(str(row.get("impact", "")))[:IMPACT_MAX_CHARS]
        selected.append(result)

    selected.sort(key=lambda x: int(x.get("score", "0")), reverse=True)
    if not selected:
        logger.warning("rank_and_summarize: 解析结果为空，使用 fallback。")
        return fallback_selection(items=items, top_n=top_n)
    return selected[:top_n]


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
            "impact": item.get("impact", ""),
        }
        for idx, item in enumerate(items)
    ]

    user_prompt = (
        "请把下面资讯字段统一改写为简体中文，必须保持事实不变。\n"
        "严格输出JSON："
        '{"items":[{"id":1,"title":"中文标题","brief":"中文摘要","impact":"中文影响"}]}\n'
        f"要求：title<={TITLE_MAX_CHARS}字，brief<={BRIEF_MAX_CHARS}字，impact<={IMPACT_MAX_CHARS}字。\n\n"
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

    localized: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            idx = int(row.get("id", 0))
        except (TypeError, ValueError):
            continue
        if idx < 1 or idx > len(items):
            continue

        item = items[idx - 1].copy()
        title_cn = clean_text(str(row.get("title", "")))[:TITLE_MAX_CHARS]
        brief_cn = clean_text(str(row.get("brief", "")))[:BRIEF_MAX_CHARS]
        impact_cn = clean_text(str(row.get("impact", "")))[:IMPACT_MAX_CHARS]

        if title_cn:
            item["title"] = title_cn
        if brief_cn:
            item["brief"] = brief_cn
        if impact_cn:
            item["impact"] = impact_cn
        localized.append(item)

    if len(localized) != len(items):
        logger.warning("localize_items_to_chinese: 本地化条目数不匹配，回退原文。")
        return items
    return localized


def polish_with_kimi(markdown: str, kimi_api_key: str, kimi_model: str) -> str:
    if not kimi_api_key:
        return markdown

    client = OpenAI(api_key=kimi_api_key, base_url="https://api.moonshot.cn/v1")
    prompt = (
        "请润色以下AI早报Markdown："
        "1) 不改事实和链接；2) 保持简洁专业；3) 不新增未提供的信息。\n\n"
        + markdown
    )
    return llm_chat(
        client=client,
        model=kimi_model,
        system_prompt="你是中文科技编辑。",
        user_prompt=prompt,
        max_tokens=2500,
    )


def render_markdown(items: list[dict[str, str]]) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# AI 早报（{today}）",
        "",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 今日要点",
    ]

    for idx, item in enumerate(items[:5], 1):
        lines.append(f"- {idx}. {item.get('brief', '')}")

    lines.append("")
    lines.append("## 详细快讯")
    for idx, item in enumerate(items, 1):
        lines.extend(
            [
                "",
                f"### {idx}) {item['title']}",
                f"- 摘要：{item.get('brief', '')}",
                f"- 影响：{item.get('impact', '')}",
                f"- 来源：{item['link']}",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    qwen_api_key = os.getenv("QWEN_API_KEY", "").strip()
    if not qwen_api_key:
        raise RuntimeError("QWEN_API_KEY 未设置")

    qwen_model = os.getenv("QWEN_MODEL", "qwen-flash")
    kimi_api_key = os.getenv("KIMI_API_KEY", "").strip()
    kimi_model = os.getenv("KIMI_MODEL", "kimi-latest")
    max_items = int(os.getenv("MAX_ITEMS", "30"))
    top_n = int(os.getenv("TOP_N", "10"))
    sources = load_sources("sources.txt")
    fetched_items = fetch_items(sources=sources, hours=36, per_source=30)
    filtered_items, rejected_stats = filter_primary_items_with_stats(fetched_items)
    items = filtered_items[:max_items]
    logger.info(
        "items fetched=%s filtered=%s kept=%s top_n=%s",
        len(fetched_items),
        len(fetched_items) - len(filtered_items),
        len(items),
        top_n,
    )
    if rejected_stats:
        logger.info("primary filter rejected reasons=%s", json.dumps(rejected_stats, ensure_ascii=False))
    if not items:
        raise RuntimeError("未抓到一手资讯，请检查 sources.txt 或放宽 STRICT_PRIMARY_ONLY 配置")

    selected = rank_and_summarize(items=items, qwen_api_key=qwen_api_key, qwen_model=qwen_model, top_n=top_n)
    selected = localize_items_to_chinese(items=selected, qwen_api_key=qwen_api_key, qwen_model=qwen_model)
    markdown = render_markdown(selected)
    markdown = polish_with_kimi(markdown=markdown, kimi_api_key=kimi_api_key, kimi_model=kimi_model)

    report_dir = Path("reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    daily = report_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    latest = report_dir / "latest.md"
    daily.write_text(markdown, encoding="utf-8")
    latest.write_text(markdown, encoding="utf-8")

    print(f"done: {daily}")


if __name__ == "__main__":
    main()
