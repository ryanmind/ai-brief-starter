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


def build_mkdocs_latest(markdown: str) -> str:
    lines = markdown.splitlines()
    updated_at = extract_updated_at(lines)
    summary = collect_summary(lines)
    items = parse_items(lines)

    output: list[str] = []
    output.append("# 今日早报")
    output.append("")
    if updated_at:
        output.append(f"> 更新时间：{updated_at}")
    else:
        output.append("> 更新时间：未知")
    output.append("> 说明：该页面由 `ai-morning-brief` 自动生成并同步。")
    output.append("")
    output.append("## 本期摘要")
    output.append("")
    if summary:
        for idx, text in enumerate(summary, start=1):
            output.append(f"{idx}. {text}")
    else:
        output.append("- 暂无摘要")
    output.append("")
    output.append("## 详细内容（点击展开）")
    output.append("")

    if not items:
        output.append("暂无详细条目。")
        output.append("")
        return "\n".join(output).rstrip() + "\n"

    for item in items:
        output.append(f'??? info "{item.index}. {item.title}"')
        output.append(f"    - **摘要**：{item.summary or '暂无'}")
        if item.detail:
            output.append(f"    - **细节**：{item.detail}")
        output.append("    - **关键点**：")
        if item.key_points:
            for point in item.key_points:
                output.append(f"        - {point}")
        else:
            output.append("        - 暂无")
        output.append(f"    - **影响分析**：{item.impact or '暂无'}")
        source = to_safe_text(item.source)
        output.append(f"    - **来源**：{source or '暂无'}")
        if item.extra_lines:
            output.append("    - **补充**：")
            for extra in item.extra_lines:
                output.append(f"        - {extra}")
        output.append("")

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
