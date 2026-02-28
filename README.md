# AI Brief Starter

这个目录可直接迁移为独立仓库使用。

## 快速开始

1. 配置 GitHub Actions Secrets
   - 必需：`QWEN_API_KEY`
   - 必需（默认严格模式）：若 `sources.txt` 含 `x.com` 账号，必须配置 `X_BEARER_TOKEN`
   - 可选：`KIMI_API_KEY`
2. 推送代码到 GitHub（建议 private 仓库）
3. 在 Actions 里手动运行 `ai-morning-brief`
4. 查看 `reports/latest.md`

## 配置 QWEN_API_KEY（6步）

1. 打开你的 GitHub 仓库页面。
2. 进入 `Settings`。
3. 左侧点击 `Secrets and variables` -> `Actions`。
4. 点击 `New repository secret`。
5. `Name` 填写 `QWEN_API_KEY`。
6. `Secret` 填入阿里百炼 API Key（`sk-...`），点击 `Add secret`。

## 首次运行检查（避免常见坑）

- 仓库默认分支要和你实际使用的分支一致（当前示例为 `master`），`schedule` 只会在默认分支触发。
- 仓库设置需允许工作流写回仓库：`Settings -> Actions -> General -> Workflow permissions -> Read and write permissions`。
- 必须配置 `QWEN_API_KEY`，未配置会在工作流里直接报错并停止。
- 默认 `STRICT_X_API_REQUIRED=1`：若保留 `x.com` 来源，未配置 `X_BEARER_TOKEN` 会直接失败。

## 目录

- `PRD.md`：需求文档
- `main.py`：采集 + 摘要 + 生成早报
- `sources.txt`：RSS 来源
- `docs/x_api_setup_zh.md`：X 官方 API 开通与 Token 配置指南
- `.github/workflows/daily.yml`：定时任务
- `reports/`：日报输出

## 说明

- 默认只用 Qwen；配置 `KIMI_API_KEY` 后才会启用 Kimi 精修。
- 当前版本不包含企业微信通知。
- 当前版本仅输出中文早报。
- 默认开启一手信息过滤（`STRICT_PRIMARY_ONLY=1`），会剔除疑似二手转述内容。
- 可用 `PRIMARY_SOURCE_DOMAINS`、`PRIMARY_X_HANDLES` 覆盖允许来源白名单（逗号分隔）。
- 可用 `SECOND_HAND_DOMAINS` 追加二手媒体域名黑名单（逗号分隔）。
- `sources.txt` 可直接写 `https://x.com/<账号>`，脚本会通过官方 X API 拉取该账号最新原创推文（需配置 `X_BEARER_TOKEN`）。
- 默认 `STRICT_X_API_REQUIRED=1`：若配置了 `x.com` 账号却没有 `X_BEARER_TOKEN`，任务会直接失败，保证来源可追溯。
- `sources.txt` 可直接写 GitHub `.../blob/<branch>/CHANGELOG.md`，脚本会自动转成对应 Atom 源。
- 默认过滤 GitHub commit hash 链接（`.../commit/<sha>`），优先保留 release/公告级信息。
- 可用 `PER_DOMAIN_LIMIT`、`ARXIV_MAX_ITEMS` 控制单域名与 arXiv 来源配额，避免单一来源刷屏。
- 默认 `TOP_N=20`，如需更全可调到 `30`（建议同时提高 `MAX_ITEMS`，例如 `120`）。
- 详细快讯会输出 `关键点` 列表（2-3条短 bullet），更适合朋友圈/飞书阅读。
- 默认不显式限制模型输出 token（仍受模型服务端上限约束）。
- 详细快讯会输出 `发布时间`（UTC ISO 时间）用于追溯信息时效。
- 可运行 `python scripts/report_quality_check.py reports/latest.md` 做质量闸门检查（标题完整率/二手域名/关键点格式）。
- 可运行 `python scripts/source_health_check.py --output reports/source_health.md` 做信息源健康检查（含 X API 账号状态）。
