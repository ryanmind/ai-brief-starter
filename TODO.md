# TODO

## 自动化流程审查（2026-03-07）

本清单基于 `skills/automation-pipeline` + `skills/ai-brief` 对当前仓库自动化链路的检查结果整理，聚焦 GitHub Actions、定时任务、文档发布、通知与可验证性。

## 当前自动化链路

1. `ai-morning-brief` 定时/手动生成早报，运行测试、生成报告、同步 docs，并提交产物到仓库。
2. `docs` 在文档变更或 `ai-morning-brief` 成功后构建并发布 GitHub Pages。
3. `source-health-check` 每周运行信源健康检查，并上传 Markdown artifact。

## P0：优先处理

- [ ] 为 `docs` workflow 增加失败告警与失败摘要
  - 现状：`.github/workflows/docs.yml` 只有 build/deploy，没有像 `daily.yml` 那样的失败通知链路。
  - 风险：早报主流程成功后，Pages 构建/部署失败可能无人感知，站点内容停留在旧版本。
  - 完成标准：`docs` 失败时至少有 1 条主动告警（飞书/微信/Issue/step summary），并带上 run URL。

- [ ] 为 `source-health-check` 增加失败告警，并把结果落到可持续查看的位置
  - 现状：`.github/workflows/source-health.yml` 只上传 `reports/source_health.md` artifact，没有告警，也没有同步到 docs 或仓库。
  - 风险：周检失败或信源大面积失效时不易被发现；artifact 也不适合作为长期面板。
  - 完成标准：失败时主动通知；成功时将结果同步到 `docs/`、仓库文件或其他固定可见位置之一。

- [ ] 新增 workflow 静态校验流程（至少覆盖 GitHub Actions YAML）
  - 现状：仓库里没有 `actionlint` / workflow lint / YAML 校验链路。
  - 风险：表达式、缩进、`if`、`needs`、`workflow_run` 这类问题只能等运行时暴露，定时任务尤其容易“夜里坏掉”。
  - 完成标准：新增独立 workflow，在 PR / push 时校验 `.github/workflows/*.yml`，并对失败直接阻断合并。

## P1：近期补齐

- [ ] 给 `source-health-check` 显式补 `permissions` 和 `concurrency`
  - 现状：`.github/workflows/source-health.yml` 没有 `permissions`，也没有 `concurrency`。
  - 风险：权限边界不清晰；手动触发与定时触发可能重叠执行。
  - 完成标准：至少显式设置只读权限，并为 workflow 增加稳定的 concurrency group。

- [ ] 为 `scripts/notify_wechat.py` 补充聚焦单测
  - 现状：测试中已有 `tests/test_resilience.py` 覆盖 `notify_feishu`，但当前未见 `notify_wechat` 对应测试。
  - 风险：微信通知的摘要提取、请求失败处理、返回值约定发生回归时，CI 不会及时发现。
  - 完成标准：至少覆盖摘要提取、Server 酱成功/失败返回、请求异常三个场景。

- [ ] 收敛 `daily.yml` 与 `src/config.py` 的默认值来源，减少配置漂移
  - 现状：`.github/workflows/daily.yml` 中维护了大量运行参数，`src/config.py` 也维护了一部分默认值。
  - 风险：同一参数在 workflow 和代码中双处定义，后续调整时容易不一致。
  - 完成标准：明确“代码默认值”和“workflow 覆盖值”的边界；能收回 `src/config.py` 的尽量收回，并在文档中说明剩余例外。

## P2：加固项

- [ ] 将 GitHub Actions 从浮动版本标签逐步收敛到固定 SHA
  - 现状：三个 workflow 仍在使用 `actions/checkout@v4`、`actions/setup-python@v5`、`actions/deploy-pages@v4` 等浮动 tag。
  - 风险：上游 action 行为漂移时，定时任务可能在未改仓库代码的情况下出现变化。
  - 完成标准：至少为核心 workflow 中的关键 action 固定到审查过的 commit SHA，并保留升级节奏说明。

- [ ] 为上传的 artifacts 增加保留策略，并明确用途
  - 现状：`daily.yml` 与 `source-health.yml` 上传 artifact，但未设置 `retention-days`。
  - 风险：artifact 过多时成本和检索体验会变差，也不利于区分“短期调试产物”和“长期归档产物”。
  - 完成标准：为不同 artifact 设定保留天数，并在文档里说明用途与查找方式。

- [ ] 给 Pages 发布补一个最小 smoke check
  - 现状：`.github/workflows/docs.yml` 在 `deploy-pages` 后即结束，没有对最终站点做可达性检查。
  - 风险：部署动作成功不等于页面可正常访问；模板、资源或路径问题可能要等人工发现。
  - 完成标准：部署后检查关键页面（至少 `/` 和 `/latest/`）返回正常状态码。

## 审查依据

- 主早报 workflow：`.github/workflows/daily.yml`
- 文档发布 workflow：`.github/workflows/docs.yml`
- 信源巡检 workflow：`.github/workflows/source-health.yml`
- 文档同步脚本：`scripts/sync_reports_to_docs.py`
- 配置中心：`src/config.py`
- 现有通知/容错测试：`tests/test_resilience.py`
