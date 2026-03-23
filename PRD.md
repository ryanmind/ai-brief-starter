# PRD - AI资讯自动早报（个人开发者版）

- 版本：v2.0
- 日期：2026-03-23
- 作者：Ryan + Kilo

## 1. 背景与上下文（会话沉淀）

本 PRD 继承了已确认前提，供后续迁移到独立仓库后直接沿用：

1. 用户不使用 OpenClaw（原因：没有可长期占用的专门电脑，不希望自建常驻服务）。
2. 采用云托管自动化（GitHub Actions）+ 模型 API（Iflow 必选，Kimi 可选）。
3. 不使用企业微信通知（当前无企业微信）。
4. Key 必须放 GitHub Actions Secrets，不写入代码。
5. 仓库建议私有（private），避免泄漏 Prompt、来源、策略、成本信息。

## 2. 产品目标

每天自动生成一份可直接发布到公众号编辑器的《AI早报》Markdown，包含：
- 今日要点（Top N，默认 20 条）
- 详细快讯（摘要、影响、关键点、来源链接）
- 历史归档（按日期保存）

## 3. 非目标

- v2 不做公众号自动发布
- v2 不做复杂可视化后台
- v2 不接入 OpenClaw

## 4. 用户与使用场景

- 用户：个人开发者/自媒体作者
- 场景：每天早晨打开仓库 `reports/latest.md`，复制到公众号编辑器后人工微调发布

## 5. 功能需求

### 5.1 数据采集

- 从 `sources.txt` 读取 RSS/GitHub/X 源列表（约 200+ 信源）
- 抓取最近 24 小时内资讯（可配置 FETCH_HOURS）
- 基于链接和标题做去重
- 支持 GitHub Trending 热门项目抓取
- 支持 X/Twitter 账号转 Nitter RSS 抓取（支持 twitterapi.io 回退）

### 5.2 资讯过滤

- **一级过滤**：筛选一手来源（官方博客、GitHub、创始人账号）
- **二级过滤**：AI 主题相关性判定（LLM 辅助）
- **三级过滤**：来源多样性限制（单源最多 30 条）
- **四级过滤**：跨天历史去重

### 5.3 资讯筛选与摘要

- 使用 LLM 进行候选资讯筛选、打分、短摘要、影响说明、关键点提取
- 默认输出 Top 20
- 支持模型：qwen3-coder-plus（默认）、自定义 fallback 模型列表

### 5.4 标题规范化

- 使用 LLM 补全缺失的主语（公司/产品/人物）
- 确保标题包含明确主体和版本号

### 5.5 多模型审核

- **低风险内容**：单模型审核
- **高风险内容**：多模型交叉审核（默认 3 个模型，阈值 2/3 通过）
- 审核标准：真实性、完整性、准确性、价值性

### 5.6 去重处理

- 同事件去重：基于内容指纹相似度判断
- 跨天去重：基于历史报告指纹库

### 5.7 成稿生成

- 生成统一 Markdown 模板
- 输出：
  - `reports/YYYY-MM-DD_HH-MM-SS.md`
  - `reports/latest.md`
- 分类平衡：模型进展、论文研究、产品与行业三类均衡

### 5.8 质量检查

- 自动修复：标题格式、关键点完整性、影响分析合规性
- 输出：`reports/quality_metrics.json`、高风险条目清单

### 5.9 定时运行

- GitHub Actions 每天北京时间 07:30–21:30 每两小时自动运行
- 支持手动触发（workflow_dispatch）

### 5.10 通知渠道

- 飞书 Webhook 通知（可选）
- 微信 Server 酱通知（可选）

### 5.11 文档同步

- 自动同步到 `docs/latest.md`
- 历史归档同步到 `docs/history/YYYY-MM-DD.md`
- 自动触发 GitHub Pages 部署

## 6. 非功能需求

- **稳定性**：失败可重跑，输出文件可追溯，支持 fail-open 降级
- **安全性**：密钥仅在 GitHub Secrets，`.env` 文件加入 `.gitignore`
- **成本可控**：默认低成本模型，MAX_ITEMS/TOP_N 可配置
- **可迁移**：目录结构可整体搬迁到独立仓库直接运行
- **可观测**：结构化日志（key=value 格式），质量指标可追溯
- **可测试**：核心逻辑单元测试覆盖，关键路径冒烟测试

## 7. 成功标准（验收）

- 连续 7 天自动产出日报文件，无人工介入运行环境
- 每日报告至少 15 条有效资讯（分类均衡）
- 每条资讯带来源链接、摘要、关键点（2-3条）、影响分析
- 质检通过率 ≥ 90%
- 未出现 API Key 泄露

## 8. 技术方案

- 运行平台：GitHub Actions
- 语言：Python 3.11
- 依赖：openai、feedparser、requests、pytest
- 模型接口：
  - Iflow（默认，必选）
  - 支持模型 failover 机制
- 缓存：LLM 响应缓存（默认 7 天）

## 9. 配置项

### 必填 Secrets
- `IFLOW_API_KEY`

### 可选 Secrets
- 飞书：`FEISHU_WEBHOOK_URL`、`FEISHU_BOT_SECRET`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`
- 微信：`SERVERCHAN_SENDKEY`
- X 回退：`TWITTERAPI_IO_KEY`

### 环境变量
| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_MODEL` | `qwen3-coder-plus` | 主模型 |
| `MAX_ITEMS` | 120 | 最大处理条数 |
| `TOP_N` | 20 | 最终输出条数 |
| `FETCH_HOURS` | 24 | 回溯小时数 |
| `USE_OPTIMIZED_PIPELINE` | 1 | 启用优化管线 |
| `REVIEW_ENABLED` | 1 | 启用多模型审核 |
| `REVIEW_MODELS` | (见 config) | 审核模型列表 |
| `REVIEW_PASS_THRESHOLD` | 2 | 审核通过阈值 |
| `STRICT_FACT_MODE` | 1 | 事实校验模式 |
| `LOG_LEVEL` | INFO | 日志级别 |

## 10. 运维监控需求

### 10.1 告警策略

- **主流程失败**：飞书/微信通知 + Actions 失败摘要
- **docs 构建失败**：独立告警（TODO）
- **信源健康检查**：每周巡检，异常通知（TODO）

### 10.2 质量指标

- `reports/quality_metrics.json`：生成数量、过滤统计、修复统计
- `reports/high_risk_items.md`：高风险未通过条目清单

### 10.3 监控任务

- 每周信源健康检查（`source-health-check` workflow）
- 生成 `reports/source_health.md` artifact

## 11. 信源管理规范

### 11.1 信源分类

- **一手来源**：官方博客、GitHub 官方仓库、创始人/官方 X 账号
- **二、三手来源**：媒体聚合、编译站点（自动过滤）

### 11.2 信源优先级

- 官方 RSS > GitHub CHANGELOG.atom > X 账号
- 核心厂商（OpenAI/Anthropic/DeepMind）优先级最高

### 11.3 信源维护

- 新增信源需通过代码审查
- 失效信源在 `source_health.md` 中标记
- 每季度审查信源列表

## 12. 内容风控（v2.0 规划）

- 敏感内容过滤（军事、医疗、金融高风险领域）
- 事实校验：关键数字/版本号与原文核对
- 引用来源可追溯

## 13. 里程碑

- M1（Day 1）：跑通首次手动触发，生成 `reports/latest.md` ✅
- M2（Day 3）：稳定每日自动生成并归档 ✅
- M3（Day 7）：优化 sources 与 Prompt，提升可发布质量 ✅
- M4（v2.0）：多模型审核、智能管线、质量检查 ✅
- M5（v2.1）：运维监控、告警增强（TODO）
- M6（v2.2）：数据分析面板、内容风控（规划中）

## 14. 风险与应对

| 风险 | 应对措施 |
|------|----------|
| RSS 不稳定 | 增加备选源，采集失败不中断全流程 |
| 输出质量波动 | 使用固定模板、更严格 prompt、多模型审核 |
| 成本超预算 | 限制 MAX_ITEMS、TOP_N，默认关闭可选功能 |
| LLM API 失败 | fallback 模型列表、fail-open 降级 |
| 定时任务失效 | 手动触发 + 失败通知兜底 |

## 15. 迁移到独立仓库说明

本目录可直接迁移为新仓库根目录：
1. 将该目录全部文件复制到新仓库根目录。
2. 在 GitHub 新仓库配置 Secrets。
3. 手动 Run 一次 workflow 验证。

## 16. 更新日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-02-27 | 初始版本，基于 Qwen/Kimi API |
| v2.0 | 2026-03-23 | 迁移到 Iflow API、添加多模型审核、优化管线、质量检查、信源管理规范、运维监控需求 |