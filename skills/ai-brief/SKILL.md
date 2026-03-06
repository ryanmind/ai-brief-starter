---
name: ai-brief
description: "用于维护 AI Brief Starter 仓库。凡是涉及本仓库定时早报流程的任务都使用此 skill，包括信源、过滤、摘要、报告生成、质量检查、文档同步、通知发送与相关 GitHub Actions。"
---

# AI Brief

## 何时使用

- 任务涉及本仓库的定时 AI 早报流程。
- 你要修改信源、过滤、摘要、成报、质检、通知、文档同步或自动化流程。

## 核心规则

- 不要直接修改 `TEMPLATE.md`；输出格式应通过代码、Prompt 或配置调整。
- 不要手工修改 `reports/` 下的生成产物。
- 面向用户的文案保持简洁，且以中文优先。
- 共享阈值、开关和环境变量默认值统一放在 `src/config.py`。
- 新增或更新清洗流程时，使用 LLM 清洗；不要新增 Python 规则式清洗逻辑。

## 标准流程

1. 先判断任务属于哪一类：信源、主流程、质检、推送、文档或 CI。
2. 只阅读与该区域直接相关的文件，不做大范围无差别扫描。
3. 在源代码或配置里修问题，不在 `reports/` 这类生成结果里打补丁。
4. 行为有变更时，补一个聚焦的回归测试。
5. 先跑最小验证命令，通过后再扩大验证范围。

## 文件地图

- 信源与过滤：`sources.txt`、`src/feed.py`、`src/filters.py`
- 摘要与成报：`main.py`、`src/llm.py`、`src/report.py`
- 质量检查：`scripts/report_quality_check.py`、`scripts/source_health_check.py`
- 推送通知：`scripts/notify_feishu.py`、`scripts/notify_wechat.py`
- 文档与流程：`docs/`、`mkdocs.yml`、`.github/workflows/`

## 验证命令

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/python scripts/report_quality_check.py reports/latest.md --autofix
.venv/bin/python scripts/source_health_check.py --output reports/source_health.md
.venv/bin/python main.py
mkdocs build --strict
```
