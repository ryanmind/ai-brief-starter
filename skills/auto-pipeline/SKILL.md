---
name: auto-pipeline
description: "用于维护代码仓库中的自动化 pipeline。凡是涉及定时或事件驱动流程、source 配置、数据采集、处理、生成、同步、通知、质量检查、发布或相关 GitHub Actions / CI 任务，都可使用此 skill。"
---

# Auto Pipeline

## 何时使用

- 任务涉及仓库中的自动化 pipeline、定时任务或 CI / GitHub Actions 流程。
- 你要修改调度时间、触发条件、输入源、source 配置、处理逻辑、生成产物、同步发布、通知或质量检查。

## 六层任务模型

- Scheduler：调度、cron、触发条件、workflow 启用状态。
- Source：数据源、鉴权、抓取窗口、rate limit、重试。
- Processing：清洗、过滤、聚合、排序、转换。
- Generate：模板、报告、构建产物、输出格式。
- Sync：发布、上传、同步、归档。
- Notify：消息通知、webhook、邮件、回调。

多步骤任务先分层，再定位文件；不要跨层打补丁。

## 核心规则

- 不直接修改生成产物；优先修改源代码、配置和 workflow。
- 先做最小范围修复，再评估是否影响上下游。
- 行为变更必须检查幂等性，避免重复生成、重复同步或重复通知。
- 输入源必须尽量配置化，不要把 source 和关键参数写死在代码里。
- 没有现成测试体系时，不额外引入重型框架；优先补聚焦验证。

## 标准流程

0. 先确认 workflow 或 job 是否启用，且确实会自动触发。
1. 判断任务属于哪一层，再锁定相关文件。
2. 只阅读与该层直接相关的文件和配置。
3. 在源头位置修复问题，不在临时产物或生成结果上打补丁。
4. 检查 cron、时区和绝对日期；GitHub Actions 的 cron 默认使用 UTC。
5. 按函数 → 脚本 → job → workflow 的顺序逐级验证。

## 文件检查清单

- 调度层：`.github/workflows/`、crontab、workflow `schedule` / `workflow_dispatch`
- 任务入口：`scripts/`、`jobs/`、`Makefile`、`package.json` scripts
- 数据采集：`clients/`、`sources/`、抓取脚本、环境变量
- 处理逻辑：pipeline 入口、filters、processors、aggregators
- 生成输出：templates、reports、output、build 相关目录
- 同步发布：publish、upload、sync、archive 相关脚本
- 通知交付：notify、webhook、email、callback 相关脚本
- 质量保障：`tests/`、quality check、health check、lint 相关脚本

## Source 配置

- 输入源及关键参数应配置在配置文件、环境变量或 workflow inputs 中。
- 至少检查这些参数：auth、rate limit、timeout、retry、backoff、dedup key、default value、time window。
- 修改 source 时，同时确认上游输入格式和下游处理逻辑仍然兼容。
- 若 source 依赖外部服务，说明本地验证前置条件，并提供失败回退或降级策略。

## 复杂任务拆分

- Scheduler / Source：确认是否触发、取什么、多久取一次、失败如何退避。
- Processing / Generate：确认如何处理、如何生成、输出是否稳定且可重复。
- Sync / Notify：确认发布到哪里、通知给谁、重复执行是否安全。

## 验证原则

- 按顺序验证：单个函数、单个脚本、单个 job、完整 workflow。
- 必须验证：时间窗口、幂等性、空数据、重复执行、失败重试。
- 若任务依赖密钥或外部服务，明确说明前置条件，以及本地无法完整验证的部分。
