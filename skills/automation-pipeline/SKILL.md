---
name: automation-pipeline
description: "分析、维护和修复代码仓库中的自动化 pipeline、CI/CD 与定时任务。用于修改 GitHub Actions、cron、自动抓取/处理/生成/同步/通知流程，或排查未触发、执行失败、重复执行、时间窗口、幂等性、外部依赖和发布失败等自动化问题。"
---

# Auto Pipeline

## 目标

- 先定位 pipeline 所在层，再在问题产生处修复。
- 保持最小改动、可重复执行和可验证。
- 优先修改源码、配置和 workflow，而不是生成产物。

## 核心规则

- 不要直接修改 `reports/`、`output/`、`build/` 等生成结果。
- 不要跨层补丁；`Source` 问题就在 `Source` 层修。
- 让关键输入走配置、环境变量或 workflow inputs，不要写死。
- 先做最小修复，再确认是否影响上下游。
- 始终检查幂等性，避免重复生成、重复同步、重复通知。

## 七层模型

- `Scheduler`：触发与调度，如 `schedule`、`push`、`workflow_dispatch`、job 开关。
- `Source`：采集与外部依赖，如 API、RSS、数据库、认证、限流、重试、时间窗口。
- `Processing`：清洗、过滤、聚合、排序、转换、去重。
- `Storage`：缓存、数据库、artifact、checkpoint、输出文件。
- `Generate`：Markdown、JSON、HTML、报告、构建产物。
- `Sync`：提交、上传、发布、远端同步。
- `Notify`：webhook、Slack、邮件、机器人通知。

## 标准流程

1. 先确认 workflow、job 和 trigger 是否存在且启用；记住 GitHub Actions 的 `cron` 默认使用 UTC。
2. 判断故障属于哪一层，只读取该层和直接依赖文件，不做全仓扫描。
3. 优先检查配置、环境变量、时间窗口、checkpoint、缓存和去重键。
4. 在源头层修复代码或配置，不在中间产物和最终产物里打补丁。
5. 按 `函数 → 脚本 → job → workflow` 逐级验证，先小范围再扩大。
6. 同时覆盖空数据、重复执行、部分失败、重试和发布/通知去重场景。

## 优先检查

- 调度：`.github/workflows/`
- 入口：`scripts/`、`jobs/`、`Makefile`、`package.json`
- 采集：`clients/`、`sources/`、抓取脚本
- 处理：`pipeline/`、`processors/`、`filters/`、`aggregators/`
- 输出：`templates/`、`reports/`、`output/`、`build/`
- 发布：`publish/`、`sync/`、`upload/`、`archive/`
- 通知：`notify/`、`webhook/`、`email/`、`callback/`
- 配置：`config/`、`.env`、`.env.example`、workflow inputs

## 重点检查项

- `Source`：`auth`、`rate limit`、`timeout`、`retry`、`backoff`、`time window`、`cursor`、`checkpoint`、`dedup key`
- `Storage`：旧缓存、旧 checkpoint、读取旧 artifact
- `Sync` / `Notify`：重复提交、重复发布、重复消息
- 时间：UTC、本地时区、抓取窗口边界、夏令时或日期换挡
- 失败：空输入、部分成功、重跑恢复、外部服务降级

## 常见误区

- 直接改生成产物而不是改源代码。
- 忽略 UTC `cron`，导致触发时间错位。
- 多层同时改动，导致行为难以推断。
- 把 source 或阈值写死在代码里。
- 不验证幂等性，导致重复产出或重复通知。
- 忽略限流、重试或 checkpoint，导致漏数或重数。
