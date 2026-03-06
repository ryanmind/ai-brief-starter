# 飞书同步最小配置指南（精简版）

本文件只保留本仓库自动同步飞书文档的必要步骤。

## 必需 Secrets

在 GitHub 仓库 `Settings -> Secrets and variables -> Actions` 中配置：

- `QWEN_API_KEY`
- `FEISHU_WEBHOOK_URL`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`

> 说明：当前工作流默认 `FEISHU_DOC_SYNC_REQUIRED=1`，即飞书通知会先创建飞书文档，再发送群消息。

## 获取 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`

1. 打开飞书开放平台：https://open.feishu.cn/  登录。  
2. 进入「开发者后台」→「创建应用」→ 选企业自建应用（和你文档同一租户）。  
3. 进入该应用的「凭证与基础信息 / 应用凭证」页面。  
4. 复制：  
   - App ID（就是 `FEISHU_APP_ID`）  
   - App Secret（就是 `FEISHU_APP_SECRET`）

## 建议的可选 Secrets

- `FEISHU_BOT_SECRET`（机器人签名）
- `FEISHU_REPORT_FOLDER_TOKEN`（飞书归档文件夹）
- `FEISHU_REPORT_DOC_URL`（飞书总览文档入口）

## 生效步骤

1. 确认本地代码已 `commit + push` 到远程 `master`。
2. 手动运行 GitHub Actions：`ai-morning-brief`。  
3. 成功后你会看到：  
   - 飞书群通知里出现“今日完整文档（飞书）”链接  
   - 飞书中新增当天文档（不会覆盖旧文档）

## 常见问题

- 缺少 `FEISHU_APP_ID`/`FEISHU_APP_SECRET`：会导致文档同步失败，飞书提醒也不会发出。  
- 机器人有关键词/签名限制：请确保消息策略与 Secret 配置一致。  
- 应用未发布或权限不足：即使凭证正确，也可能无法创建/写入文档。
