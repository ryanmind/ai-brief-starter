# PRD - AI资讯自动早报（个人开发者版）

- 版本：v1.0
- 日期：2026-02-27
- 作者：Ryan + Codex

## 1. 背景与上下文（会话沉淀）

本 PRD 继承了已确认前提，供后续迁移到独立仓库后直接沿用：

1. 用户不使用 OpenClaw（原因：没有可长期占用的专门电脑，不希望自建常驻服务）。
2. 采用云托管自动化（GitHub Actions）+ 模型 API（Qwen 必选，Kimi 可选）。
3. 不使用企业微信通知（当前无企业微信）。
4. Key 必须放 GitHub Actions Secrets，不写入代码。
5. 仓库建议私有（private），避免泄漏 Prompt、来源、策略、成本信息。

## 2. 产品目标

每天自动生成一份可直接发布到公众号编辑器的《AI早报》Markdown，包含：
- 今日要点（Top N）
- 详细快讯（摘要、影响、来源链接）
- 历史归档（按日期保存）

## 3. 非目标

- v1 不做公众号自动发布
- v1 不做复杂可视化后台
- v1 不接入 OpenClaw

## 4. 用户与使用场景

- 用户：个人开发者/自媒体作者
- 场景：每天早晨打开仓库 `reports/latest.md`，复制到公众号编辑器后人工微调发布

## 5. 功能需求

### 5.1 数据采集

- 从 `sources.txt` 读取 RSS 源列表
- 抓取最近 36 小时内资讯
- 基于链接和标题做去重

### 5.2 资讯筛选与摘要

- 使用 Qwen 进行候选资讯筛选、打分、短摘要、影响说明
- 默认输出 Top 10

### 5.3 成稿生成

- 生成统一 Markdown 模板
- 输出：
  - `reports/YYYY-MM-DD.md`
  - `reports/latest.md`

### 5.4 可选精修

- 若存在 `KIMI_API_KEY`，再调用 Kimi 对初稿做语言润色（不改事实和链接）

### 5.5 定时运行

- GitHub Actions 每天北京时间 07:30 自动运行
- 支持手动触发（workflow_dispatch）

## 6. 非功能需求

- 稳定性：失败可重跑，输出文件可追溯
- 安全性：密钥仅在 GitHub Secrets
- 成本可控：默认低成本 Qwen 模型，Kimi 可按需开启
- 可迁移：目录结构可整体搬迁到独立仓库直接运行

## 7. 成功标准（验收）

- 连续 7 天自动产出日报文件，无人工介入运行环境
- 每日报告至少 8 条有效资讯
- 每条资讯带来源链接
- 未出现 API Key 泄露

## 8. 技术方案

- 运行平台：GitHub Actions
- 语言：Python 3.11
- 依赖：openai、feedparser、python-dateutil
- 模型接口：
  - Qwen（阿里 DashScope OpenAI 兼容）
  - Kimi（Moonshot OpenAI 兼容，可选）

## 9. 配置项

- 必填 Secrets：
  - `QWEN_API_KEY`
- 可选 Secrets：
  - `KIMI_API_KEY`
- 环境变量：
  - `QWEN_MODEL`（默认 `qwen-flash`）
  - `KIMI_MODEL`（默认 `kimi-latest`）
  - `MAX_ITEMS`（默认 `30`）
  - `TOP_N`（默认 `10`）

## 10. 里程碑

- M1（当天）：跑通首次手动触发，生成 `reports/latest.md`
- M2（3天）：稳定每日自动生成并归档
- M3（7天）：优化 sources 与 Prompt，提升可发布质量

## 11. 风险与应对

- RSS 不稳定：增加备选源，采集失败不中断全流程
- 输出质量波动：使用固定模板和更严格 prompt
- 成本超预算：限制 MAX_ITEMS、TOP_N，并默认关闭 Kimi 精修

## 12. 迁移到独立仓库说明

本目录 `docs/ai-brief-starter` 可直接迁移为新仓库根目录：
1. 将该目录全部文件复制到新仓库根目录。
2. 在 GitHub 新仓库配置 Secrets。
3. 手动 Run 一次 workflow 验证。

