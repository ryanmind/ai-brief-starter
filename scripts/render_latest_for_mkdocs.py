#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path


SUMMARY_HEADER = "### 📌 本期摘要"
SUMMARY_HEADERS = (SUMMARY_HEADER, "## 今日要点", "## 30秒导读")
ITEM_HEADER_PATTERN = re.compile(r"^###\s+(\d+)[\.\)、)]\s+(.+)$")
MARKDOWN_LINK_PATTERN = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<url>[^)]+)\)")
URL_PATTERN = re.compile(r"https?://[^\s)]+")
MANUAL_TAG_PATTERN = re.compile(r"(?<!\w)#([A-Za-z][A-Za-z0-9_-]*|[\u4e00-\u9fff]{1,8})")
MANUAL_DIRECTIVE_PATTERN = re.compile(r"\[(?:cat|category|分类)\s*:\s*([A-Za-z\u4e00-\u9fff_-]+)\]", re.IGNORECASE)

CATEGORY_MODEL = "model"
CATEGORY_PAPER = "paper"
CATEGORY_PRODUCT = "product"
CATEGORY_ORDER = (CATEGORY_MODEL, CATEGORY_PAPER, CATEGORY_PRODUCT)
CATEGORY_LABELS = {
    CATEGORY_MODEL: "🤖 模型进展",
    CATEGORY_PAPER: "🧪 论文研究",
    CATEGORY_PRODUCT: "🏢 产品与行业",
}
CATEGORY_ICONS = {
    CATEGORY_MODEL: "material/robot-outline",
    CATEGORY_PAPER: "material/flask-outline",
    CATEGORY_PRODUCT: "material/office-building-outline",
}
MODEL_KEYWORDS = (
    "gpt",
    "gemini",
    "claude",
    "grok",
    "qwen",
    "llama",
    "deepseek",
    "mistral",
    "llm",
    "模型",
    "模型卡",
    "system card",
    "flash",
    "instant",
)
MODEL_WEAK_KEYWORDS = ("agent", "推理", "reasoning", "inference")
PAPER_STRONG_KEYWORDS = ("arxiv", "论文", "预印本", "preprint")
PRODUCT_KEYWORDS = (
    "发布",
    "上线",
    "推出",
    "更新",
    "版本",
    "sdk",
    "融资",
    "合作",
    "平台",
    "生态",
    "changelog",
    "release",
    "投资",
    "并购",
    "收购",
)
PRODUCT_STRONG_KEYWORDS = (
    "融资",
    "并购",
    "收购",
    "合作",
    "版本",
    "release",
    "changelog",
)
MANUAL_CATEGORY_ALIASES = {
    "model": CATEGORY_MODEL,
    "models": CATEGORY_MODEL,
    "llm": CATEGORY_MODEL,
    "模型": CATEGORY_MODEL,
    "paper": CATEGORY_PAPER,
    "research": CATEGORY_PAPER,
    "论文": CATEGORY_PAPER,
    "product": CATEGORY_PRODUCT,
    "industry": CATEGORY_PRODUCT,
    "business": CATEGORY_PRODUCT,
    "产品": CATEGORY_PRODUCT,
    "行业": CATEGORY_PRODUCT,
}


@dataclass
class BriefItem:
    index: str
    title: str
    summary: str = ""
    detail: str = ""
    key_points: list[str] = field(default_factory=list)
    impact: str = ""
    source: str = ""
    extra_lines: list[str] = field(default_factory=list)


def extract_updated_at(lines: list[str]) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## 📰 AI 早报"):
            parts = [part.strip() for part in stripped.split("·", maxsplit=1)]
            if len(parts) == 2 and parts[1]:
                return parts[1]
        if stripped.startswith("生成时间："):
            return stripped.removeprefix("生成时间：").strip()
    return ""


def normalize_summary_line(line: str) -> str:
    text = line.strip()
    text = re.sub(r"^-\s*\d+\.\s*", "", text)
    text = re.sub(r"^-\s*", "", text)
    return text.strip()


def collect_summary(lines: list[str]) -> list[str]:
    collecting = False
    summary: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped in SUMMARY_HEADERS:
            collecting = True
            continue
        if collecting and ITEM_HEADER_PATTERN.match(stripped):
            break
        if collecting and stripped.startswith("-"):
            normalized = normalize_summary_line(stripped)
            if normalized:
                summary.append(normalized)
    return summary


def parse_items(lines: list[str]) -> list[BriefItem]:
    items: list[BriefItem] = []
    current: BriefItem | None = None
    in_key_points = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        header_match = ITEM_HEADER_PATTERN.match(stripped)
        if header_match:
            if current:
                items.append(current)
            current = BriefItem(index=header_match.group(1), title=header_match.group(2).strip())
            in_key_points = False
            continue

        if not current:
            continue

        if stripped.startswith("**摘要**："):
            current.summary = stripped.removeprefix("**摘要**：").strip()
            in_key_points = False
            continue
        if stripped.startswith("- 摘要："):
            current.summary = stripped.removeprefix("- 摘要：").strip()
            in_key_points = False
            continue
        if stripped.startswith("- 细节："):
            current.detail = stripped.removeprefix("- 细节：").strip()
            in_key_points = False
            continue
        if stripped == "**关键点**":
            in_key_points = True
            continue
        if stripped == "- 关键点：":
            in_key_points = True
            continue
        if stripped.startswith("**影响分析**："):
            current.impact = stripped.removeprefix("**影响分析**：").strip()
            in_key_points = False
            continue
        if stripped.startswith("- 影响："):
            current.impact = stripped.removeprefix("- 影响：").strip()
            in_key_points = False
            continue
        if stripped.startswith("**来源**："):
            current.source = stripped.removeprefix("**来源**：").strip()
            in_key_points = False
            continue
        if stripped.startswith("- 来源："):
            current.source = stripped.removeprefix("- 来源：").strip()
            in_key_points = False
            continue

        if in_key_points and stripped.startswith("- "):
            point = stripped[2:].strip()
            if point:
                current.key_points.append(point)
            continue

        if stripped:
            current.extra_lines.append(stripped)

    if current:
        items.append(current)
    return items


def to_safe_text(markdown_or_text: str) -> str:
    markdown_or_text = markdown_or_text.strip()
    if not markdown_or_text:
        return ""
    link = MARKDOWN_LINK_PATTERN.search(markdown_or_text)
    if link:
        return f"[{link.group('label')}]({link.group('url')})"
    return markdown_or_text


def normalize_manual_tag(token: str) -> str:
    return token.strip().lower().replace("-", "_")


def detect_manual_category(item: BriefItem) -> str | None:
    text_fields = [item.title, item.summary, item.detail, item.impact, *item.key_points, *item.extra_lines, item.source]
    for text in text_fields:
        if not text:
            continue
        for directive in MANUAL_DIRECTIVE_PATTERN.finditer(text):
            category = MANUAL_CATEGORY_ALIASES.get(normalize_manual_tag(directive.group(1)))
            if category:
                return category
        for hashtag in MANUAL_TAG_PATTERN.finditer(text):
            category = MANUAL_CATEGORY_ALIASES.get(normalize_manual_tag(hashtag.group(1)))
            if category:
                return category
    return None


def strip_manual_category_tags(text: str) -> str:
    if not text:
        return text

    def _replace_directive(match: re.Match[str]) -> str:
        token = normalize_manual_tag(match.group(1))
        return "" if token in MANUAL_CATEGORY_ALIASES else match.group(0)

    def _replace_hashtag(match: re.Match[str]) -> str:
        token = normalize_manual_tag(match.group(1))
        return "" if token in MANUAL_CATEGORY_ALIASES else match.group(0)

    cleaned = MANUAL_DIRECTIVE_PATTERN.sub(_replace_directive, text)
    cleaned = MANUAL_TAG_PATTERN.sub(_replace_hashtag, cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def extract_url(markdown_or_text: str) -> str:
    if not markdown_or_text:
        return ""
    link = MARKDOWN_LINK_PATTERN.search(markdown_or_text)
    if link:
        return link.group("url").strip()
    url = URL_PATTERN.search(markdown_or_text)
    if url:
        return url.group(0).strip()
    return ""


def compact_text(text: str) -> str:
    if not text:
        return ""
    text = strip_manual_category_tags(text)
    without_links = MARKDOWN_LINK_PATTERN.sub(lambda match: match.group("label"), text)
    collapsed = re.sub(r"\s+", " ", without_links).strip()
    return collapsed.strip("。")


def truncate_text(text: str, limit: int = 72) -> str:
    compacted = compact_text(text)
    if len(compacted) <= limit:
        return compacted
    trimmed = compacted[: limit - 1].rstrip(" ,，。；;：:")
    return f"{trimmed}…"


def classify_item(item: BriefItem) -> str:
    manual_category = detect_manual_category(item)
    if manual_category:
        return manual_category

    source_url = extract_url(item.source).lower()
    text_blob = " ".join([item.title, item.summary, item.detail, item.impact, *item.key_points]).lower()
    paper_blob = " ".join([item.title, item.summary, item.source]).lower()

    if "arxiv.org" in source_url or any(keyword in paper_blob for keyword in PAPER_STRONG_KEYWORDS):
        return CATEGORY_PAPER

    model_score = 0
    product_score = 0

    model_score += sum(2 for keyword in MODEL_KEYWORDS if keyword in text_blob)
    model_score += sum(1 for keyword in MODEL_WEAK_KEYWORDS if keyword in text_blob)

    product_score += sum(2 for keyword in PRODUCT_STRONG_KEYWORDS if keyword in text_blob)
    product_score += sum(1 for keyword in PRODUCT_KEYWORDS if keyword in text_blob)

    if "github.com" in source_url:
        product_score += 2
    if "openai.com" in source_url and any(keyword in source_url for keyword in ("/gpt-", "/system-card")):
        model_score += 2

    if model_score >= product_score + 1:
        return CATEGORY_MODEL
    if product_score > 0:
        return CATEGORY_PRODUCT
    if any(domain in source_url for domain in ("x.com", "nitter.net", "github.com", "openai.com")):
        return CATEGORY_PRODUCT
    return CATEGORY_PRODUCT


def group_items_by_category(items: list[BriefItem]) -> dict[str, list[BriefItem]]:
    grouped = {key: [] for key in CATEGORY_ORDER}
    for item in items:
        grouped[classify_item(item)].append(item)
    return grouped


def choose_item_preview(item: BriefItem, limit: int = 86) -> str:
    for candidate in (item.impact, item.summary, item.detail):
        text = truncate_text(candidate, limit=limit)
        if text:
            return text
    return "暂无概览"


def escape_admonition_title(text: str) -> str:
    return text.replace('"', '\\"')


def append_item_block(output: list[str], item: BriefItem) -> None:
    cleaned_title = strip_manual_category_tags(item.title)
    cleaned_summary = strip_manual_category_tags(item.summary)
    cleaned_detail = strip_manual_category_tags(item.detail)
    cleaned_impact = strip_manual_category_tags(item.impact)

    output.append(f'??? info "{item.index}. {escape_admonition_title(cleaned_title)}"')
    output.append(f"    - **摘要**：{cleaned_summary or '暂无'}")
    if cleaned_detail:
        output.append(f"    - **细节**：{cleaned_detail}")
    output.append("    - **关键点**：")
    if item.key_points:
        for point in item.key_points:
            output.append(f"        - {strip_manual_category_tags(point)}")
    else:
        output.append("        - 暂无")
    output.append(f"    - **影响分析**：{cleaned_impact or '暂无'}")
    source = to_safe_text(item.source)
    output.append(f"    - **来源**：{source or '暂无'}")
    if item.extra_lines:
        output.append("    - **补充**：")
        for extra in item.extra_lines:
            output.append(f"        - {strip_manual_category_tags(extra)}")
    output.append("")


def build_mkdocs_latest(markdown: str) -> str:
    lines = markdown.splitlines()
    updated_at = extract_updated_at(lines)
    summary = collect_summary(lines)
    items = parse_items(lines)
    grouped_items = group_items_by_category(items)
    top_items = items[:5]

    output: list[str] = []
    output.append("# 今日早报")
    output.append("")
    if updated_at:
        output.append(f"> 更新时间：{updated_at}")
    else:
        output.append("> 更新时间：未知")
    output.append("> 说明：该页面由 `ai-morning-brief` 自动生成并同步。")
    output.append("")
    output.append("## 今日看板")
    output.append("")
    output.append('<div class="grid cards brief-kpi-grid" markdown>')
    output.append("")
    output.append("- :material/clock-outline: **更新时间**  ")
    output.append(f"  {updated_at or '未知'}")
    output.append("- :material/format-list-numbered: **快讯总数**  ")
    output.append(f"  {len(items)} 条")
    for category in CATEGORY_ORDER:
        output.append(f"- :{CATEGORY_ICONS[category]}: **{CATEGORY_LABELS[category]}**  ")
        output.append(f"  {len(grouped_items[category])} 条")
    output.append("")
    output.append("</div>")
    output.append("")
    output.append("## 本期摘要")
    output.append("")
    if summary:
        for idx, text in enumerate(summary, start=1):
            output.append(f"{idx}. {strip_manual_category_tags(text)}")
    else:
        output.append("- 暂无摘要")
    output.append("")
    output.append("## TOP 5 快速导读")
    output.append("")
    if top_items:
        output.append('<div class="grid cards brief-top-grid" markdown>')
        output.append("")
        for item in top_items:
            preview = choose_item_preview(item)
            output.append(f"- **{item.index}. {strip_manual_category_tags(item.title)}**  ")
            output.append(f"  {preview}")
        output.append("")
        output.append("</div>")
    else:
        output.append("- 暂无条目")
    output.append("")
    output.append("## 分类速览")
    output.append("")
    for category in CATEGORY_ORDER:
        label = CATEGORY_LABELS[category]
        category_items = grouped_items[category]
        output.append(f'=== "{label}（{len(category_items)}）"')
        if category_items:
            for item in category_items[:8]:
                preview = choose_item_preview(item, limit=48)
                output.append(f"    - **{item.index}. {strip_manual_category_tags(item.title)}**：{preview}")
        else:
            output.append("    - 暂无条目")
        output.append("")
    output.append("## 全部快讯（按分类折叠）")
    output.append("")

    if not items:
        output.append("暂无详细条目。")
        output.append("")
        return "\n".join(output).rstrip() + "\n"

    for category in CATEGORY_ORDER:
        category_items = grouped_items[category]
        output.append(f"### {CATEGORY_LABELS[category]}（{len(category_items)}）")
        output.append("")
        if not category_items:
            output.append("暂无条目。")
            output.append("")
            continue
        for item in category_items:
            append_item_block(output, item)

    return "\n".join(output).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render reports/latest.md into docs-friendly latest.md.")
    parser.add_argument("source", help="Source markdown file, typically reports/latest.md")
    parser.add_argument("target", help="Target markdown file, typically docs/latest.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = Path(args.source)
    target_path = Path(args.target)

    if not source_path.exists():
        raise FileNotFoundError(f"source file not found: {source_path}")

    rendered = build_mkdocs_latest(source_path.read_text(encoding="utf-8"))
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
