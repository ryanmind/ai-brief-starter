# AI Brief Starter

自动抓取一手 AI 资讯，生成中文早报，并同步到文档站与通知渠道。

- 在线文档：https://ryanmind.github.io/ai-brief-starter/
- 默认工作流：`ai-morning-brief`（`.github/workflows/daily.yml`）
- 调度频率：北京时间 **07:30–21:30 每两小时一次**

## 功能概览

- 抓取官方 RSS / GitHub / X 信源
- 过滤非一手内容与非 AI 主题内容
- LLM 排名、摘要、中文化、标题补全
- 多模型审核 + 跨天去重 + 同事件去重
- 生成 `reports/latest.md`
- 自动同步 `docs/latest.md` 与 `docs/history/`
- 支持飞书 / 微信通知

## 快速开始

### 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
export IFLOW_API_KEY=your_key
python main.py
```

运行后主要产物：

- `reports/latest.md`：最新早报
- `reports/YYYY-MM-DD.md`：归档报告
- `reports/quality_metrics.json`：质检结果

### GitHub Actions

必需 Secret：

- `IFLOW_API_KEY`

可选 Secret：

- 飞书：`FEISHU_WEBHOOK_URL`、`FEISHU_BOT_SECRET`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`
- 微信：`SERVERCHAN_SENDKEY`
- X 回退抓取：`TWITTERAPI_IO_KEY`

首次使用建议确认：

- 默认分支设置正确
- Actions 具有 `contents: write`
- 在 Actions 手动运行一次 `ai-morning-brief`

## 常用命令

```bash
python -m pytest tests/ -v
python scripts/report_quality_check.py reports/latest.md --autofix
python scripts/source_health_check.py --output reports/source_health.md
mkdocs serve
mkdocs build --strict
```

## 项目结构

```text
main.py                 主流程入口
src/                    采集、过滤、LLM、报告逻辑
scripts/                质检、通知、文档同步等脚本
tests/                  pytest 测试
reports/                运行产物
docs/                   MkDocs 文档源文件
.github/workflows/      自动化工作流
```

## 更多文档

- 快速开始：`docs/quick-start.md`
- 配置说明：`docs/configuration.md`
- 信源维护：`docs/sources.md`
