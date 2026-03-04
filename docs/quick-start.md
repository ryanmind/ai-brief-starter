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
export QWEN_API_KEY="sk-xxxxxx"  # 阿里百炼 API Key
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
| `QWEN_API_KEY` | ✅ | 阿里百炼 API Key，主流程必需 |
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
3. 选择分支（`master` 或 `mkdocs`）
4. 点击 `Run workflow`

### 3. 自动定时

工作流已配置北京时间每天 07:30 自动运行：

```yaml
schedule:
  - cron: "30 23 * * *"  # UTC 23:30 = Beijing 07:30
```

> 注意：`schedule` 仅在仓库默认分支触发，请确保默认分支与实际使用分支一致。

### 4. 自动发布到文档站

- `ai-morning-brief` 成功后会自动将 `reports/latest.md` 渲染为可读性更高的文档页，再同步到 `docs/latest.md`
- 同时将 `reports/YYYY-MM-DD.md` 同步为 `docs/history/YYYY-MM-DD.md`
- 同步有变化时会自动提交到当前分支
- `docs` 工作流会检测到 `docs/**` 变更并发布到 GitHub Pages

---

## 常见问题

### Q: 运行失败提示缺少 QWEN_API_KEY

确保已在 GitHub Secrets 中配置 `QWEN_API_KEY`。

### Q: 为什么没有飞书提醒？

先检查 `FEISHU_WEBHOOK_URL`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET` 是否都已配置。当前默认 `FEISHU_DOC_SYNC_REQUIRED=1`，缺少应用凭证会导致飞书通知步骤失败。

### Q: 为什么没有微信提醒？

检查是否配置 `SERVERCHAN_SENDKEY`，并确认 `ai-morning-brief` 中 `Notify WeChat` 步骤执行成功。

### Q: 为什么 GitHub Pages 上“今日早报”没更新？

确认 `ai-morning-brief` 已成功，并且日志里出现 `Commit docs latest brief` 步骤；随后 `docs` 工作流会自动部署。

### Q: 在哪里查看历史早报？

在文档站打开“历史归档”页面（`/history/`），可按日期访问 `history/YYYY-MM-DD.md`。

### Q: 如何获取阿里百炼 API Key？

1. 访问 [阿里百炼](https://bailian.console.aliyun.com/)
2. 开通服务
3. 创建 API Key

### Q: 如何添加新的信息源？

编辑 `sources.txt`，每行一个 RSS 链接：

```
https://example.com/feed.xml
https://x.com/username
https://github.com/owner/repo/releases.atom
```
