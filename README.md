# AI Brief Starter

AI 资讯自动早报生成器 —— 每天 07:30 自动生成 AI 行业早报，推送至飞书。

📚 **[在线文档](https://ryanmind.github.io/ai-brief-starter/)**

## 快速开始

1. 配置 GitHub Actions Secrets
   - 必需：`QWEN_API_KEY`
   - 推送通知（二选一或同时配置）：
     - 飞书：`FEISHU_WEBHOOK_URL`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`
     - 微信：`SERVERCHAN_SENDKEY`
2. 推送代码到 GitHub（建议 private 仓库）
3. 在 Actions 里手动运行 `ai-morning-brief`
4. 在飞书或微信查看通知，或在 Actions 下载 `ai-brief-reports` artifact

## 微信推送配置（Server酱）

每天早报生成后自动推送到微信，方便转发朋友圈/小红书。

### 获取 SendKey

1. 访问 https://sct.ftqq.com/
2. 微信扫码登录
3. 复制你的 **SendKey**

### 配置 GitHub Secret

在仓库 `Settings` → `Secrets and variables` → `Actions` 添加：

| Secret 名称 | 值 |
|------------|-----|
| `SERVERCHAN_SENDKEY` | 你的 SendKey |

配置后，每天早报生成完成会收到微信消息，可直接复制转发。

## 配置 QWEN_API_KEY（6步）

1. 打开你的 GitHub 仓库页面。
2. 进入 `Settings`。
3. 左侧点击 `Secrets and variables` -> `Actions`。
4. 点击 `New repository secret`。
5. `Name` 填写 `QWEN_API_KEY`。
6. `Secret` 填入阿里百炼 API Key（`sk-...`），点击 `Add secret`。

## 首次运行检查（避免常见坑）

- 仓库默认分支要和你实际使用的分支一致（当前示例为 `master`），`schedule` 只会在默认分支触发。
- 工作流不会回写 `reports/`，但会回写 `docs/latest.md` 与 `docs/history/**`，因此 `ai-morning-brief` 需要 `contents: write`。
- 必须配置 `QWEN_API_KEY`，未配置会在工作流里直接报错并停止。

## 目录

- `main.py`：采集 + 摘要 + 生成早报
- `sources.txt`：RSS 来源
- `scripts/`：辅助脚本（飞书通知、质量检查、源健康检查）
- `src/config.py`：配置常量
- `tests/`：单元测试
- `reports/`：运行时产物目录（默认不提交到 Git）
- `docs/`：MkDocs 文档源文件
- `mkdocs.yml`：MkDocs 配置文件
- `PRD.md`：需求文档
- `TEMPLATE.md`：早报模板标准文件

## 文档站点

本项目使用 MkDocs + GitHub Pages 托管文档：

- **在线文档**：https://ryanmind.github.io/ai-brief-starter/
- **源文件**：`docs/` 目录
- **本地预览**：`mkdocs serve`

详见 `docs/mkdocs-tutorial.md` 搭建教程。

## 说明

- 默认使用 Qwen 生成与本地化，不再依赖额外润色模型。
- 当前版本不包含企业微信通知。
- 当前版本仅输出中文早报。
- 默认开启一手信息过滤（`STRICT_PRIMARY_ONLY=1`），会剔除疑似二手转述内容。
- 默认开启 AI 主题过滤（`STRICT_AI_TOPIC_ONLY=1`），会剔除非 AI 主题内容；可用 `AI_TOPIC_KEYWORDS`（逗号分隔）补充关键词。
- 可用 `PRIMARY_SOURCE_DOMAINS`、`PRIMARY_X_HANDLES` 覆盖允许来源白名单（逗号分隔）。
- 可用 `SECOND_HAND_DOMAINS` 追加二手媒体域名黑名单（逗号分隔）。
- `sources.txt` 可直接写 `https://x.com/<账号>`，脚本会自动转成 Nitter RSS（可用 `NITTER_RSS_BASES` 配置多个实例，逗号分隔）。
- `sources.txt` 可直接写 GitHub `.../blob/<branch>/CHANGELOG.md`，脚本会自动转成对应 Atom 源。
- 默认过滤 GitHub commit hash 链接（`.../commit/<sha>`），优先保留 release/公告级信息。
- 可用 `PER_DOMAIN_LIMIT`、`ARXIV_MAX_ITEMS` 控制单域名与 arXiv 来源配额，避免单一来源刷屏。
- 默认 `TOP_N=20`，如需更全可调到 `30`（建议同时提高 `MAX_ITEMS`，例如 `120`）。
- 默认开启跨天去重（`HISTORY_DEDUP_DAYS=2`），会自动避开最近两天已发过的相同资讯链接/标题。
- 工作流会缓存去重索引（`HISTORY_STATE_PATH`，默认 `reports/history_index.json`），即使不提交 `reports/` 也能跨运行去重。
- 可用 `HISTORY_STATE_MAX_DAYS` 控制去重索引保留天数（默认 `14`）。
- 若条目不足会自动扩大抓取窗口（`FETCH_HOURS=24`，`FALLBACK_FETCH_HOURS=72`），尽量补足 `TOP_N`。
- 可用 `PER_SOURCE_ITEMS` 提高单源抓取条数（默认 `30`），提升候选池丰富度。
- 详细快讯按模板输出 `摘要/关键点/影响分析/来源`，并输出 `关键点` 列表（2-3条短 bullet），更适合朋友圈/公众号发布。
- 标题会强制补全主语（公司/产品/账号等），避免出现“release:4.6.3”“5.4即将上线”这类无主语标题。
- 默认开启最终文案润色（`FINAL_POLISH_ENABLED=1`）：由 Qwen 提升可读性；若结构/链接/数字校验不通过会自动回退原稿。
- 可用 `BRIEF_MAX_CHARS`、`DETAIL_MAX_CHARS`、`IMPACT_MAX_CHARS` 调整每条内容长度（默认 160/260/140）。
- `DETAIL_*` 参数仅用于内部抽取与事实约束，不会直接作为模板展示字段输出。
- 默认开启事实保守模式（`STRICT_FACT_MODE=1`），若摘要与原文重合度过低或出现新数字，会自动回退到抽取式写法。
- 可用 `FACT_OVERLAP_MIN` 调整事实重合阈值（默认 `0.55`，越高越保守）。
- 渲染后会执行自动修复与二次质检，保障结构完整与事实一致性。
- 质检缺陷默认仅告警不阻断发布；若存在缺陷会在飞书通知中追加“质检提醒”。
- `QUALITY_CHECK_FAIL_OPEN` 已兼容保留，不再用于阻断发布控制。
- 默认不显式限制模型输出 token（仍受模型服务端上限约束）。
- 配置 `FEISHU_WEBHOOK_URL` 后，工作流会自动发送日报摘要到飞书群；配置 `FEISHU_APP_ID/FEISHU_APP_SECRET` 后会自动新建飞书文档并写入全文（不会覆盖历史）。
- 飞书文档写入会自动去除 Markdown 标记，默认以可读正文样式展示（非原始 Markdown 状态）。
- 工作流默认开启飞书文档外链公开（`FEISHU_DOC_PUBLIC_READABLE=1`）并强制校验（`FEISHU_DOC_PUBLIC_REQUIRED=1`），确保群里发送的是可外部访问链接。
- 默认不在群消息中展示 GitHub Actions 任务详情；如需展示可设置 `FEISHU_INCLUDE_RUN_URL=1`。
- 如配置 `FEISHU_REPORT_FOLDER_TOKEN`，每日新文档会创建在指定文件夹；`FEISHU_REPORT_DOC_URL` 可作为总览入口链接附在消息中。
- `FEISHU_DOC_SYNC_REQUIRED` 默认 `1`，未配置文档写入凭证会直接失败；如仅需群通知可设为 `0`。
- 默认不跟踪 `reports/*.md`，工作流通过 artifact 与飞书保留结果。
- 可运行 `python scripts/report_quality_check.py reports/latest.md --autofix` 做质量闸门检查并自动修复摘要/关键点字段（标题完整率/二手域名/关键点格式）。
- 可运行 `python scripts/source_health_check.py --output reports/source_health.md` 做信息源健康检查。
