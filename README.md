# AI Brief Starter

这个目录可直接迁移为独立仓库使用。

## 快速开始

1. 配置 GitHub Actions Secrets
   - 必需：`QWEN_API_KEY`
   - 可选：`KIMI_API_KEY`、`FEISHU_WEBHOOK_URL`、`FEISHU_BOT_SECRET`、`FEISHU_REPORT_DOC_URL`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_REPORT_FOLDER_TOKEN`、`FEISHU_DOC_SYNC_REQUIRED`
2. 推送代码到 GitHub（建议 private 仓库）
3. 在 Actions 里手动运行 `ai-morning-brief`
4. 在飞书查看通知与“今日完整文档（飞书）”，或在 Actions 下载 `ai-brief-reports` artifact

## 配置 QWEN_API_KEY（6步）

1. 打开你的 GitHub 仓库页面。
2. 进入 `Settings`。
3. 左侧点击 `Secrets and variables` -> `Actions`。
4. 点击 `New repository secret`。
5. `Name` 填写 `QWEN_API_KEY`。
6. `Secret` 填入阿里百炼 API Key（`sk-...`），点击 `Add secret`。

## 首次运行检查（避免常见坑）

- 仓库默认分支要和你实际使用的分支一致（当前示例为 `master`），`schedule` 只会在默认分支触发。
- 工作流不再回写 `reports/` 到仓库，默认 `contents: read` 即可运行。
- 必须配置 `QWEN_API_KEY`，未配置会在工作流里直接报错并停止。

## 目录

- `PRD.md`：需求文档
- `main.py`：采集 + 摘要 + 生成早报
- `sources.txt`：RSS 来源
- `scripts/notify_feishu.py`：将日报推送到飞书群机器人
- `docs/feishu_docs_guide_zh.md`：飞书文档与飞书同步教程
- `.github/workflows/daily.yml`：定时任务
- `reports/`：运行时产物目录（默认不提交到 Git）

## 说明

- 默认只用 Qwen；配置 `KIMI_API_KEY` 后才会启用 Kimi 精修。
- 当前版本不包含企业微信通知。
- 当前版本仅输出中文早报。
- 默认开启一手信息过滤（`STRICT_PRIMARY_ONLY=1`），会剔除疑似二手转述内容。
- 可用 `PRIMARY_SOURCE_DOMAINS`、`PRIMARY_X_HANDLES` 覆盖允许来源白名单（逗号分隔）。
- 可用 `SECOND_HAND_DOMAINS` 追加二手媒体域名黑名单（逗号分隔）。
- `sources.txt` 可直接写 `https://x.com/<账号>`，脚本会自动转成 Nitter RSS（可用 `NITTER_RSS_BASES` 配置多个实例，逗号分隔）。
- `sources.txt` 可直接写 GitHub `.../blob/<branch>/CHANGELOG.md`，脚本会自动转成对应 Atom 源。
- 默认过滤 GitHub commit hash 链接（`.../commit/<sha>`），优先保留 release/公告级信息。
- 可用 `PER_DOMAIN_LIMIT`、`ARXIV_MAX_ITEMS` 控制单域名与 arXiv 来源配额，避免单一来源刷屏。
- 默认 `TOP_N=20`，如需更全可调到 `30`（建议同时提高 `MAX_ITEMS`，例如 `120`）。
- 默认开启跨天去重（`HISTORY_DEDUP_DAYS=2`），会自动避开最近两天已发过的相同资讯链接/标题。
- 若条目不足会自动扩大抓取窗口（`FETCH_HOURS=24`，`FALLBACK_FETCH_HOURS=72`），尽量补足 `TOP_N`。
- 可用 `PER_SOURCE_ITEMS` 提高单源抓取条数（默认 `30`），提升候选池丰富度。
- 详细快讯包含 `摘要/细节/关键点/影响`，并输出 `关键点` 列表（2-3条短 bullet），更适合朋友圈/公众号发布。
- 可用 `BRIEF_MAX_CHARS`、`DETAIL_MAX_CHARS`、`IMPACT_MAX_CHARS` 调整每条内容长度（默认 160/260/140）。
- 默认不显式限制模型输出 token（仍受模型服务端上限约束）。
- 配置 `FEISHU_WEBHOOK_URL` 后，工作流会自动发送日报摘要到飞书群；配置 `FEISHU_APP_ID/FEISHU_APP_SECRET` 后会自动新建飞书文档并写入全文（不会覆盖历史）。
- 飞书文档写入会自动去除 Markdown 标记，默认以可读正文样式展示（非原始 Markdown 状态）。
- 默认会尝试将新建飞书文档设为“组织外获得链接可读”（`FEISHU_DOC_PUBLIC_READABLE=1`）；若租户策略不允许会降级为默认权限并打印警告。
- 可设 `FEISHU_DOC_PUBLIC_REQUIRED=1`，在无法设置公开权限时让任务直接失败。
- 默认不在群消息中展示 GitHub Actions 任务详情；如需展示可设置 `FEISHU_INCLUDE_RUN_URL=1`。
- 如配置 `FEISHU_REPORT_FOLDER_TOKEN`，每日新文档会创建在指定文件夹；`FEISHU_REPORT_DOC_URL` 可作为总览入口链接附在消息中。
- `FEISHU_DOC_SYNC_REQUIRED` 默认 `1`，未配置文档写入凭证会直接失败；如仅需群通知可设为 `0`。
- 默认不跟踪 `reports/*.md`，工作流通过 artifact 与飞书保留结果。
- 可运行 `python scripts/report_quality_check.py reports/latest.md` 做质量闸门检查（标题完整率/二手域名/关键点格式）。
- 可运行 `python scripts/source_health_check.py --output reports/source_health.md` 做信息源健康检查。
