#!/usr/bin/env python3
"""
微信推送通知脚本（Server酱）
用于推送早报摘要和新文档更新通知到微信
"""

import os
import sys
from pathlib import Path

import requests


def send_wechat_message(title: str, content: str, send_key: str) -> bool:
    """
    通过 Server酱 发送微信消息

    Args:
        title: 消息标题
        content: 消息内容（支持 Markdown）
        send_key: Server酱 SendKey

    Returns:
        是否发送成功
    """
    url = f"https://sctapi.ftqq.com/{send_key}.send"
    payload = {
        "title": title,
        "desp": content,
    }

    try:
        resp = requests.post(url, data=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 0:
            print(f"微信推送成功: {title}")
            return True
        else:
            print(f"微信推送失败: {result.get('message', '未知错误')}")
            return False
    except requests.RequestException as e:
        print(f"微信推送异常: {e}")
        return False


def extract_brief_summary(report_path: Path) -> str:
    """从报告中提取简要摘要用于推送"""
    try:
        content = report_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"读取报告失败: {e}")
        return "报告生成完成，请查看详情。"

    lines = content.splitlines()
    summary_lines = []
    in_summary = False
    count = 0

    for line in lines:
        # 提取摘要部分
        if "本期摘要" in line or "📌" in line:
            in_summary = True
            continue
        if in_summary:
            if line.startswith("###") or line.startswith("---"):
                break
            if line.strip().startswith("-"):
                summary_lines.append(line)
                count += 1
                if count >= 3:
                    break

    if summary_lines:
        return "\n".join(summary_lines)

    # 提取前几条标题
    titles = []
    for line in lines:
        if line.startswith("### ") and "·" in line:
            title = line.replace("### ", "").strip()
            # 移除日期部分
            if "·" in title:
                title = title.split("·")[-1].strip()
            titles.append(f"- {title}")
            if len(titles) >= 5:
                break

    if titles:
        return "今日要点：\n" + "\n".join(titles)

    return "AI 早报已生成，请查看完整内容。"


def notify_new_brief(report_path: Path, send_key: str, doc_url: str = "") -> bool:
    """
    推送早报更新通知

    Args:
        report_path: 早报文件路径
        send_key: Server酱 SendKey
        doc_url: 飞书文档链接（可选）

    Returns:
        是否推送成功
    """
    summary = extract_brief_summary(report_path)

    # 构建消息内容
    content = f"## 📰 AI 早报已更新\n\n"
    content += f"{summary}\n\n"

    if doc_url:
        content += f"[📄 查看完整文档]({doc_url})\n\n"

    content += "---\n"
    content += "💡 可直接复制转发到朋友圈或小红书"

    return send_wechat_message(
        title="📰 AI 早报已更新",
        content=content,
        send_key=send_key,
    )


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="微信推送通知")
    parser.add_argument("report_path", help="早报文件路径")
    parser.add_argument("--doc-url", default="", help="飞书文档链接")
    parser.add_argument("--test", action="store_true", help="发送测试消息")

    args = parser.parse_args()

    send_key = os.getenv("SERVERCHAN_SENDKEY")
    if not send_key:
        print("错误: 未配置 SERVERCHAN_SENDKEY 环境变量")
        sys.exit(1)

    report_path = Path(args.report_path)

    if args.test:
        success = send_wechat_message(
            title="测试消息",
            content="这是一条测试消息，用于验证微信推送配置是否正确。",
            send_key=send_key,
        )
    else:
        if not report_path.exists():
            print(f"错误: 报告文件不存在: {report_path}")
            sys.exit(1)

        success = notify_new_brief(
            report_path=report_path,
            send_key=send_key,
            doc_url=args.doc_url,
        )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
