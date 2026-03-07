---
name: automation-pipeline
description: "诊断和修复 GitHub Actions、CI/CD、cron 与仓库自动化问题。用于 workflow/job/step 未触发、被跳过、执行失败、重复执行，或涉及 filters、if、permissions、secrets、runner、cache、artifact、matrix、workflow_call、concurrency、发布/通知幂等性的问题。"
---

# GitHub Actions Pipeline

## 目标

- 先确认 GitHub Actions 编排是否正确，再下钻到脚本和业务代码。
- 在故障产生处修复，避免跨层补丁。
- 保持最小改动、可重复执行和可验证。

## 核心规则

- 不要直接修改 `reports/`、`output/`、`build/` 等生成结果。
- 不要把 branch、path、time window、threshold、release target 写死在代码里。
- 优先让关键输入走 workflow inputs、环境变量、配置文件或 job outputs。
- 始终检查幂等性，避免重复生成、重复同步、重复发布、重复通知。
- 默认最小化 `permissions`；需要写权限时显式声明。
- 优先将第三方 action 固定到 commit SHA，而不是浮动 tag。

## 操作流程

1. 先读 `.github/workflows/` 与 workflow 调用链，确认 `on:`、filters、`if:`、`needs`、`permissions`、`concurrency`。
2. 只沿执行链路扩展阅读：被调用脚本、配置来源、cache/artifact/checkpoint、发布与通知脚本。
3. 先修 workflow 编排与配置问题；仅在编排正确后再修改脚本或业务代码。
4. 按 `函数 → 脚本 → job → workflow` 逐级验证，先最小复现，再扩大范围。

## 读取指引

- 遇到 GitHub Actions 细节问题时，读取 `references/github-actions.md`。
- 优先读取与当前故障直接相关的小节，不要整份通读。
- 重点查：trigger routing、`permissions`、`GITHUB_TOKEN`、fork PR、`workflow_call`、`matrix`、`concurrency`、cache/artifact、定时任务时区。

## 验证要求

- 先做静态检查：YAML 结构、inputs/outputs 名称、`needs` 链路、表达式和缩进。
- 再做最小验证：只跑被改动的脚本或最小 job。
- 再做链路验证：覆盖空输入、部分成功、失败重跑、缓存命中或失效、发布或通知去重。
- 涉及定时任务时，同时核对 UTC 与目标业务时区。
- 涉及发布或通知时，确认重复触发不会产生重复副作用。
