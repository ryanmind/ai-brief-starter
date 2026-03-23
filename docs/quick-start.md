# 快速开始

本指南帮助你在 5 分钟内跑通 AI 早报生成、通知与文档发布。

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

```bash
export IFLOW_API_KEY="your-api-key"  # iFlow API Key
```

### 5. 运行

```bash
python main.py
```

输出文件：
- `reports/latest.md` - 最新早报
- `reports/YYYY-MM-DD.md` - 按日期归档

---

## GitHub Actions 自动化

### 1. 配置 Secrets

进入 GitHub 仓库 `Settings` → `Secrets and variables` → `Actions`：

| Secret | 必需 | 说明 |
|--------|------|------|
| `IFLOW_API_KEY` | ✅ | iFlow API Key，主流程必需 |
| `FEISHU_WEBHOOK_URL` | 条件必需 | 需要飞书通知时填写 |
| `FEISHU_APP_ID` | 条件必需 | 当启用飞书通知时必需（当前默认强制文档同步） |
| `FEISHU_APP_SECRET` | 条件必需 | 当启用飞书通知时必需（当前默认强制文档同步） |
| `SERVERCHAN_SENDKEY` | ❌ | 微信通知（Server酱） |
| `FEISHU_REPORT_FOLDER_TOKEN` | ❌ | 飞书文档归档目录 |
| `FEISHU_REPORT_DOC_URL` | ❌ | 飞书总览文档链接 |
| `FEISHU_BOT_SECRET` | ❌ | 飞书机器人签名密钥 |

### 2. 手动触发

1. 进入 `Actions` 标签页
2. 选择 `ai-morning-brief` 工作流
3. 选择分支 `master`
4. 点击 `Run workflow`

### 3. 自动定时

工作流默认在北京时间 **07:30–21:30 每两小时执行一次**，首个时段为 07:30：

```yaml
schedule:
  - cron: "30 23 * * *"  # UTC 23:30 = Beijing 07:30
  - cron: "30 1 * * *"   # UTC 01:30 = Beijing 09:30
  - cron: "30 3 * * *"   # UTC 03:30 = Beijing 11:30
  - cron: "30 5 * * *"   # UTC 05:30 = Beijing 13:30
  - cron: "30 7 * * *"   # UTC 07:30 = Beijing 15:30
  - cron: "30 9 * * *"   # UTC 09:30 = Beijing 17:30
  - cron: "30 11 * * *"  # UTC 11:30 = Beijing 19:30
  - cron: "30 13 * * *"  # UTC 13:30 = Beijing 21:30
```

> 注意：`schedule` 仅在仓库默认分支触发，请确保默认分支与实际使用分支一致。

### 4. 自动发布到文档站

- `ai-morning-brief` 成功后会自动将 `reports/latest.md` 渲染为可读性更高的文档页，再同步到 `docs/latest.md`
- 同时将 `reports/YYYY-MM-DD.md` 同步为 `docs/history/YYYY-MM-DD.md`
- 同步有变化时会自动提交到当前分支
- `docs` 工作流会在 `ai-morning-brief` 成功后通过 `workflow_run` 自动发布到 GitHub Pages；直接推送文档相关改动到 `master` 也会触发部署

### 5. 飞书同步最小配置

若需要飞书群通知 + 飞书文档同步，至少配置以下 Secrets：

- `FEISHU_WEBHOOK_URL`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

当前工作流默认 `FEISHU_DOC_SYNC_REQUIRED=1`，缺少应用凭证会导致飞书文档同步失败。

获取 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`：

1. 打开飞书开放平台：https://open.feishu.cn/
2. 创建企业自建应用
3. 进入「凭证与基础信息 / 应用凭证」
4. 复制 App ID 和 App Secret

可选 Secrets：

- `FEISHU_BOT_SECRET`
- `FEISHU_REPORT_FOLDER_TOKEN`
- `FEISHU_REPORT_DOC_URL`

### 6. 文档站本地预览

```bash
pip install -r requirements.txt -r requirements-docs.txt
mkdocs serve
```

访问 `http://127.0.0.1:8000`。

---

## 常见问题

### Q: 运行失败提示缺少 IFLOW_API_KEY

确保已在 GitHub Secrets 中配置 `IFLOW_API_KEY`。

### Q: 为什么没有飞书提醒？

先检查 `FEISHU_WEBHOOK_URL`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET` 是否都已配置。当前默认 `FEISHU_DOC_SYNC_REQUIRED=1`，缺少应用凭证会导致飞书通知步骤失败。

### Q: 飞书文档创建失败怎么办？

优先检查：

- 应用是否与目标文档同一租户
- 应用是否已发布或具备对应权限
- 机器人签名与 `FEISHU_BOT_SECRET` 是否匹配

### Q: 为什么没有微信提醒？

检查是否配置 `SERVERCHAN_SENDKEY`，并确认 `ai-morning-brief` 中 `Notify WeChat` 步骤执行成功。

### Q: 为什么 GitHub Pages 上“今日早报”没更新？

确认 `ai-morning-brief` 已成功，并且日志里出现 `Commit docs and report outputs` 步骤；随后 `docs` 工作流会通过 `workflow_run` 自动部署。

### Q: 手动跑了 docs workflow，但没有新早报？

`docs` 工作流只负责构建与发布，不负责抓取和生成内容。先运行 `ai-morning-brief`。

### Q: 为什么文档站部署成功但页面 404？

检查：

1. `Settings -> Pages` 的 Source 是否为 `GitHub Actions`
2. 访问路径是否为 `https://ryanmind.github.io/ai-brief-starter/`
3. 是否刚部署完成，等待 1-3 分钟后再刷新

### Q: 在哪里查看历史早报？

在文档站打开“历史归档”页面（`/history/`），可按日期访问 `history/YYYY-MM-DD.md`。

### Q: 如何添加新的信息源？

编辑 `sources.txt`，每行一个 RSS 链接：

```
https://example.com/feed.xml
https://x.com/username
https://github.com/owner/repo/releases.atom
```
