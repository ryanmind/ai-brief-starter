#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest


def pick_highlights(markdown: str, max_items: int = 5) -> list[str]:
    lines = markdown.splitlines()
    in_section = False
    highlights: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## 今日要点"):
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and stripped.startswith("- "):
            highlights.append(stripped[2:].strip())
            if len(highlights) >= max_items:
                break

    return highlights


def build_feishu_sign(secret: str) -> tuple[str, str]:
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), string_to_sign, digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(digest).decode("utf-8")
    return timestamp, sign


def extract_title(markdown: str) -> str:
    match = re.search(r"^#\s+(.+)$", markdown, flags=re.M)
    if not match:
        return "AI 早报"
    return match.group(1).strip()


def post_to_feishu(webhook_url: str, payload: dict[str, object]) -> dict[str, object]:
    req = urlrequest.Request(
        url=webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urlerror.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urlerror.URLError as exc:
        raise RuntimeError(f"request failed: {exc}") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid json response: {raw}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"unexpected response payload: {raw}")
    return parsed


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/notify_feishu.py reports/latest.md")
        return 1

    report_path = Path(sys.argv[1])
    if not report_path.exists():
        print(f"skip: report not found: {report_path}")
        return 0

    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("skip: FEISHU_WEBHOOK_URL is empty")
        return 0

    markdown = report_path.read_text(encoding="utf-8")
    title = extract_title(markdown)
    highlights = pick_highlights(markdown, max_items=5)
    run_url = os.getenv("ACTIONS_RUN_URL", "").strip()

    text_lines = [f"AI早报已生成：{title}"]
    if highlights:
        text_lines.append("")
        for idx, item in enumerate(highlights, 1):
            text_lines.append(f"{idx}. {item}")
    if run_url:
        text_lines.append("")
        text_lines.append(f"任务详情：{run_url}")

    payload: dict[str, object] = {
        "msg_type": "text",
        "content": {"text": "\n".join(text_lines)},
    }

    bot_secret = os.getenv("FEISHU_BOT_SECRET", "").strip()
    if bot_secret:
        timestamp, sign = build_feishu_sign(bot_secret)
        payload["timestamp"] = timestamp
        payload["sign"] = sign

    response = post_to_feishu(webhook_url=webhook_url, payload=payload)
    code = str(response.get("code", ""))
    if code not in {"0", ""}:
        raise RuntimeError(f"feishu rejected message: {response}")

    print("notify success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
