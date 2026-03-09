# GitHub Actions Reference

## 目录

- Trigger routing
- Permissions and trust
- Orchestration
- State, Caching, and Idempotency
- Security guardrails
- Debugging and Diagnostics
- Validation checklist

## Trigger routing

- 先确认 workflow 文件位于默认分支，尤其是 `schedule` 场景。
- `schedule` 使用 UTC，最短间隔为 5 分钟。
- 排查“没触发”时，先看 `on:` 的事件类型，再看 `branches`、`branches-ignore`、`paths`、`paths-ignore`、`types`。
- `if:` 可出现在 job 和 step 上；很多 run 不是失败，而是被条件跳过。
- `workflow_dispatch`、`repository_dispatch`、`workflow_call` 各自的 inputs 和触发链不同，不要混用心智。
- 由仓库 `GITHUB_TOKEN` 触发的事件通常不会再次触发新的 workflow run；排查递归链路或“push 后没再触发”时先检查这里。

## Permissions and trust

- 默认最小化 `permissions`；不要依赖模糊的默认值心智。
- `contents: write`、`pull-requests: write`、`actions: write`、`id-token: write` 等权限都应按需显式声明。
- fork PR 默认不可信；不要假设 secrets、write token 或 deployment approval 一定可用。
- `pull_request` 与 `pull_request_target` 的信任边界不同；后者更危险，不要为了跑通而扩大权限。
- 使用 environment 时，检查 required reviewers、wait timer、environment secrets 是否阻塞 job。
- reusable workflow 不会自动继承你以为会继承的一切；显式检查 inputs、secrets、permissions、outputs。

## Orchestration

- 先看 `needs` 链是否完整，再看 job outputs 是否真的被上游写出。
- `strategy.matrix` 排查 include、exclude、fail-fast、条件分支与汇总逻辑。
- `concurrency` 是解决重复运行、重复发布、重复通知的首选机制；给生成、发布、通知链路设置稳定 group。
- 只有明确需要时才启用 `cancel-in-progress`；某些发布任务更适合串行，不适合取消。
- 调查 reusable workflow 时，先对齐调用方和被调用方的 inputs 名、outputs 名和 secrets 名。
- composite action 问题优先检查输入名、默认 shell、相对路径和工作目录。
- runner 差异要显式核对：`ubuntu-latest`、`macos-latest`、`windows-latest` 的 shell、路径、工具链都可能不同。

## State, Caching, and Idempotency

- cache 具有不可变性 (immutability)：一旦针对特定的 key 生成就不能覆盖。要合理设计 `restore-keys` 的 fallback 策略。
- cache 只用于加速，不要把旧 cache 当成新的事实来源；排查依赖或包管理器缓存失效时要注意锁文件哈希。
- artifact 是某次 run 的输出，不要把旧 artifact 当成本次输入，除非链路就是这么设计的。
- checkpoint、cursor、dedup key、上次发布时间戳，是排查漏跑、重跑、重复通知的高频入口。
- 发布和通知链路要有幂等键；仅靠“这次大概不会重复触发”不可靠。
- 时间窗口统一核对 UTC、本地时区、抓取窗口边界、夏令时与日期换挡。
- 失败重跑时，确认部分成功的副作用是否已落地，避免二次提交、二次发布、二次推送。

## Security guardrails

- 第三方 action 尽量固定到 commit SHA，而不是浮动 tag，防止供应链攻击。
- 不要把 secrets、webhook、token、cloud credentials 写入仓库、生成产物或日志。
- 对 OIDC 场景，检查 `id-token: write`、云端 trust policy 与受众配置是否一致。
- 不要为了临时修复而把 workflow 改成广域高权限。
- 只在确有必要时使用 `pull_request_target`、self-hosted runner、repository-level write token。

## Debugging and Diagnostics

- **开启详细日志**：可以通过在 Repository Variables 或 Secrets 中设置 `ACTIONS_STEP_DEBUG=true` 和 `ACTIONS_RUNNER_DEBUG=true` 来获取底层执行指纹。
- **本地复现**：提示或尝试使用 [nektos/act](https://github.com/nektos/act) 在本地容器中最小化复现故障，避免在云端频繁推送调试代码。
- **SSH 调试**：可通过类似 `mxschmitt/action-tmate` 或 `tailscale/github-action` 的 action 中间插入 breakpoint 以进入 runner 环境查错。

## Validation checklist

- 先做静态检查：YAML、表达式、inputs/outputs、`needs`、`if:`、缩进。
- 再做最小验证：只运行被改脚本、最小 job、最小 matrix 分支。
- 再做链路验证：覆盖空输入、部分成功、失败重跑、缓存命中或失效、发布或通知去重。
- 涉及 `schedule` 时，给出 UTC 与业务时区的具体对应时间，不要只写“每天早上”。
- 涉及权限或 secrets 时，明确说明依赖的仓库设置、environment 设置与 fork 行为。
