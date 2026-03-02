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

API_BASE = "https://open.feishu.cn"
DEFAULT_DOC_BASE_URL = "https://feishu.cn/docx"


def is_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def pick_highlights(markdown: str, max_items: int = 5) -> list[str]:
    lines = markdown.splitlines()
    in_section = False
    highlights: list[str] = []
    highlight_headers = ("## 今日要点", "## 30秒导读")

    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(header) for header in highlight_headers):
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and stripped.startswith("- "):
            highlights.append(stripped[2:].strip())
            if len(highlights) >= max_items:
                break

    return highlights


def normalize_highlight_item(text: str) -> str:
    normalized = re.sub(r"^\s*(?:[-*•]\s*)*(?:\d+\s*[\.\)、]\s*)+", "", text).strip()
    return normalized or text.strip()


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
    return http_json_request(
        method="POST",
        url=webhook_url,
        payload=payload,
        headers={"Content-Type": "application/json"},
    )


def http_json_request(
    method: str,
    url: str,
    payload: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(url=url, data=body, headers=req_headers, method=method)
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


def ensure_openapi_success(response: dict[str, object], action: str) -> None:
    code = response.get("code")
    if code is None:
        return
    if str(code) not in {"0", ""}:
        raise RuntimeError(f"{action} failed: {response}")


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    response = http_json_request(
        method="POST",
        url=f"{API_BASE}/open-apis/auth/v3/tenant_access_token/internal",
        payload={"app_id": app_id, "app_secret": app_secret},
    )
    ensure_openapi_success(response, action="get tenant_access_token")
    token = str(response.get("tenant_access_token", "")).strip()
    if not token:
        raise RuntimeError(f"tenant_access_token missing: {response}")
    return token


def create_docx_document(token: str, title: str, folder_token: str) -> str:
    payload: dict[str, object] = {"title": title}
    if folder_token:
        payload["folder_token"] = folder_token

    response = http_json_request(
        method="POST",
        url=f"{API_BASE}/open-apis/docx/v1/documents",
        payload=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    ensure_openapi_success(response, action="create docx document")
    data = response.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"create document failed: {response}")

    document = data.get("document")
    if isinstance(document, dict):
        doc_id = str(document.get("document_id", "")).strip()
        if doc_id:
            return doc_id
    doc_id = str(data.get("document_id", "")).strip()
    if doc_id:
        return doc_id
    raise RuntimeError(f"document_id missing in response: {response}")


def markdown_to_text_blocks(markdown: str) -> list[str]:
    blocks: list[str] = []
    in_key_points = False

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            if blocks and blocks[-1] != "":
                blocks.append("")
            in_key_points = False
            continue

        if stripped.startswith("# "):
            blocks.append(stripped[2:].strip())
            blocks.append("")
            in_key_points = False
            continue
        if stripped.startswith("## "):
            blocks.append(f"【{stripped[3:].strip()}】")
            in_key_points = False
            continue
        if stripped.startswith("### "):
            blocks.append(stripped[4:].strip())
            in_key_points = False
            continue
        if stripped.startswith("- 关键点"):
            blocks.append("关键点：")
            in_key_points = True
            continue
        if (
            stripped.startswith("- 摘要")
            or stripped.startswith("- 细节")
            or stripped.startswith("- 影响")
            or stripped.startswith("- 来源")
        ):
            blocks.append(stripped[2:].strip())
            in_key_points = False
            continue
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            blocks.append(f"• {item}")
            continue
        if stripped == "---":
            blocks.append("——")
            continue

        blocks.append(stripped)
        in_key_points = False

    return blocks


def create_docx_children(token: str, document_id: str, lines: list[str], batch_size: int = 20) -> None:
    if not lines:
        lines = ["（空内容）"]

    for start in range(0, len(lines), batch_size):
        batch = lines[start : start + batch_size]
        text_children: list[dict[str, object]] = []
        paragraph_children: list[dict[str, object]] = []
        for line in batch:
            content = line if line else " "
            text_children.append(
                {
                    "block_type": 2,
                    "text": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": content,
                                }
                            }
                        ]
                    },
                }
            )
            paragraph_children.append(
                {
                    "block_type": 2,
                    "paragraph": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": content,
                                }
                            }
                        ]
                    },
                }
            )

        url = f"{API_BASE}/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children?document_revision_id=-1"
        try:
            response = http_json_request(
                method="POST",
                url=url,
                payload={"children": text_children},
                headers={"Authorization": f"Bearer {token}"},
            )
            ensure_openapi_success(response, action="append docx blocks")
        except Exception:
            # Different tenants/versions may require `paragraph` instead of `text`.
            response = http_json_request(
                method="POST",
                url=url,
                payload={"children": paragraph_children},
                headers={"Authorization": f"Bearer {token}"},
            )
            ensure_openapi_success(response, action="append docx blocks (paragraph fallback)")


def sync_markdown_to_new_doc(markdown: str, title: str) -> str:
    app_id = os.getenv("FEISHU_APP_ID", "").strip()
    app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()
    sync_required = is_enabled(os.getenv("FEISHU_DOC_SYNC_REQUIRED"), default=True)
    if not app_id or not app_secret:
        if sync_required:
            raise RuntimeError("FEISHU_APP_ID/FEISHU_APP_SECRET missing")
        return ""

    folder_token = os.getenv("FEISHU_REPORT_FOLDER_TOKEN", "").strip()
    token = get_tenant_access_token(app_id=app_id, app_secret=app_secret)
    document_id = create_docx_document(token=token, title=title[:120], folder_token=folder_token)
    create_docx_children(token=token, document_id=document_id, lines=markdown_to_text_blocks(markdown))

    doc_base_url = os.getenv("FEISHU_DOC_BASE_URL", DEFAULT_DOC_BASE_URL).strip().rstrip("/")
    return f"{doc_base_url}/{document_id}"


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
    include_run_url = is_enabled(os.getenv("FEISHU_INCLUDE_RUN_URL"), default=False)
    run_url = os.getenv("ACTIONS_RUN_URL", "").strip()
    feishu_doc_url = os.getenv("FEISHU_REPORT_DOC_URL", "").strip()
    report_public_url = os.getenv("REPORT_PUBLIC_URL", "").strip()
    synced_doc_url = ""

    try:
        synced_doc_url = sync_markdown_to_new_doc(markdown=markdown, title=title)
    except Exception as exc:
        raise RuntimeError(f"sync report to feishu doc failed: {exc}") from exc

    text_lines = [f"AI早报已生成：{title}"]
    if highlights:
        text_lines.append("")
        for idx, item in enumerate(highlights, 1):
            text_lines.append(f"{idx}. {normalize_highlight_item(item)}")
    full_report_url = synced_doc_url or feishu_doc_url or report_public_url
    if full_report_url:
        text_lines.append("")
        if synced_doc_url:
            text_lines.append(f"今日完整文档（飞书）：{full_report_url}")
        elif feishu_doc_url:
            text_lines.append(f"全文文档（飞书总览）：{full_report_url}")
        else:
            text_lines.append(f"全文内容：{full_report_url}")
    if include_run_url and run_url:
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
