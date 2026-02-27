from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import feedparser
from dateutil import parser as dtparser
from openai import OpenAI


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


def load_sources(path: str = "sources.txt") -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


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
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()
    return json.loads(raw)


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
        '{"items":[{"id":1,"score":90,"brief":"...","impact":"..."}]}\n'
        f"最多返回{top_n}条；brief<=70字；impact<=60字；必须基于输入，不编造。\n\n"
        + "\n".join(candidates)
    )

    raw = llm_chat(
        client=client,
        model=qwen_model,
        system_prompt="你是严谨的科技新闻编辑，只输出JSON。",
        user_prompt=user_prompt,
    )
    data = extract_json(raw)

    selected: list[dict[str, str]] = []
    for row in data.get("items", []):
        idx = int(row.get("id", 0))
        if idx < 1 or idx > len(items):
            continue
        result = items[idx - 1].copy()
        result["score"] = str(int(row.get("score", 0)))
        result["brief"] = clean_text(str(row.get("brief", "")))[:120]
        result["impact"] = clean_text(str(row.get("impact", "")))[:120]
        selected.append(result)

    selected.sort(key=lambda x: int(x.get("score", "0")), reverse=True)
    return selected[:top_n]


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
    qwen_api_key = os.getenv("QWEN_API_KEY", "").strip()
    if not qwen_api_key:
        raise RuntimeError("QWEN_API_KEY 未设置")

    qwen_model = os.getenv("QWEN_MODEL", "qwen-flash")
    kimi_api_key = os.getenv("KIMI_API_KEY", "").strip()
    kimi_model = os.getenv("KIMI_MODEL", "kimi-latest")
    max_items = int(os.getenv("MAX_ITEMS", "30"))
    top_n = int(os.getenv("TOP_N", "10"))

    sources = load_sources("sources.txt")
    items = fetch_items(sources=sources, hours=36, per_source=30)[:max_items]
    if not items:
        raise RuntimeError("未抓到资讯，请检查 sources.txt")

    selected = rank_and_summarize(items=items, qwen_api_key=qwen_api_key, qwen_model=qwen_model, top_n=top_n)
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
