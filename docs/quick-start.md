---
title: 快速开始
description: 5 分钟内跑通 AI 早报生成、通知与文档发布
---

# 快速开始

本指南帮助你在 5 分钟内跑通 AI 早报生成、通知与文档发布。

## 环境要求

| 依赖 | 版本要求 |
|------|---------|
| Python | >= 3.11 |
| pip | 最新版 |

## 本地运行

### 1. 克隆仓库

```bash
git clone https://github.com/ryanmind/ai-brief-starter.git
cd ai-brief-starter
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API Key

!!! warning "必需配置"
    `QWEN_API_KEY` 是必填的 API Key，否则程序无法运行。

```bash
export QWEN_API_KEY="your-dashscope-api-key"
```

### 5. 运行

```bash
python main.py
```

运行后会在 `reports/` 目录生成：
- `latest.md` — 最新早报
- `YYYY-MM-DD.md` — 按日期归档

---

## GitHub Actions 自动化

### 1. 配置 Secrets

进入仓库 `Settings` → `Secrets and variables` → `Actions`，添加以下 Secrets：

| Secret | 必需 | 说明 |
|--------|------|------|
| `QWEN_API_KEY` | :material-check: | DashScope API Key |
| `FEISHU_WEBHOOK_URL` | 条件 | 飞书群通知 |
| `FEISHU_APP_ID` | 条件 | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 条件 | 飞书应用 App Secret |
| `SERVERCHAN_SENDKEY` | :material-close: | 微信通知（可选） |
| `TWITTERAPI_IO_KEY` | :material-close: | Twitter API Key（可选） |

!!! info "飞书配置说明"
    当前默认 `FEISHU_DOC_SYNC_REQUIRED=1`，缺少应用凭证会导致飞书文档同步失败。

### 2. 触发方式

=== "手动触发"
    1. 进入 `Actions` 标签页
    2. 选择 `ai-morning-brief` 工作流
    3. 选择分支 `master`
    4. 点击 `Run workflow`

=== "自动定时"
    默认在北京时间 **07:30–21:30 每两小时执行一次**：

    ```yaml
    # UTC 23:30 = Beijing 07:30
    # UTC 01:30 = Beijing 09:30
    # ... 以此类推至 UTC 13:30 = Beijing 21:30
    ```

### 3. 自动发布到文档站

```
ai-morning-brief 成功
  → 渲染 reports/latest.md 为可读格式
  → 同步到 docs/latest.md
  → 同步历史到 docs/history/YYYY-MM-DD.md
  → 提交到 master
  → 触发 docs workflow
  → 部署到 GitHub Pages
```

---

## 飞书应用创建

获取 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`：

1. 打开 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 进入「凭证与基础信息」→ 复制 App ID 和 App Secret
4. 发布应用并配置权限

可选 Secrets：

| Secret | 说明 |
|--------|------|
| `FEISHU_BOT_SECRET` | 飞书机器人签名密钥 |
| `FEISHU_REPORT_FOLDER_TOKEN` | 飞书文档归档目录 |
| `FEISHU_REPORT_DOC_URL` | 飞书总览文档链接 |

---

## 本地预览文档站

```bash
pip install -r requirements.txt -r requirements-docs.txt
mkdocs serve
```

访问 `http://127.0.0.1:8000`

---

## 常见问题

### 运行失败提示缺少 QWEN_API_KEY

确保已在环境变量或 GitHub Secrets 中配置 `QWEN_API_KEY`。

### 没有飞书/微信通知？

先检查 Secrets 配置是否完整。当前默认 `FEISHU_DOC_SYNC_REQUIRED=1`，缺少应用凭证会导致通知步骤失败。

### 飞书文档创建失败？

优先检查：
- 应用是否与目标文档同一租户
- 应用是否已发布或具备对应权限
- 机器人签名与 `FEISHU_BOT_SECRET` 是否匹配

### GitHub Pages 没更新？

确认 `ai-morning-brief` 已成功，检查日志是否有 `Commit docs and report outputs` 步骤。部署后等待 1-3 分钟。

### 文档站 404？

1. `Settings` → `Pages` 的 Source 是否为 `GitHub Actions`
2. 访问路径是否为 `https://ryanmind.github.io/ai-brief-starter/`
3. 刚部署完等 1-3 分钟后再刷新

### 如何添加新的信息源？

编辑 `sources.txt`，每行一个来源：

```text
https://example.com/feed.xml
https://x.com/username
https://github.com/owner/repo/releases.atom
```
