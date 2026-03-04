# 问题清单（ERROR）

> 更新时间：2026-03-04  
> 说明：该页同步自仓库根目录 `ERROR.md`，用于在文档站公开跟踪关键问题。

## 1) 通知失败被静默吞掉（高优先级）

- 位置：`.github/workflows/daily.yml`
- 现象：`Notify Feishu`、`Notify WeChat` 使用 `continue-on-error: true`，通知失败不阻断流程。
- 影响：日报已生成但无人收到提醒，运营无法及时感知异常。
- 建议：通知失败时追加显式告警，并区分“可选失败”和“配置错误导致必然失败”。

## 2) AI 主题过滤误判（高优先级）

- 位置：`src/config.py`、`main.py`
- 现象：当前主要基于子串匹配，容易把非 AI 内容误判为 AI。
- 影响：早报混入非 AI 条目，内容质量下降。
- 建议：升级为词边界/规则 + LLM 二次判定（可疑条目）。

## 3) Docs 部署触发重复与竞态（中高优先级）

- 位置：`.github/workflows/docs.yml`
- 现象：同时监听 `push` 与 `workflow_run`，可能重复部署。
- 影响：偶发不是最新页面、重复构建。
- 建议：收敛触发路径并统一并发分组策略。

## 4) README 与实际权限不一致（已修复）

- 位置：`README.md`
- 现象（历史）：文案曾写 `contents: read` 即可，但 daily workflow 需要 `contents: write`（要回写 `docs/`）。
- 影响：维护者按旧文档配置会遇到权限错误。
- 当前：`README.md` 已与 workflow 权限保持一致。

## 5) 质检策略需改造（中优先级）

- 位置：`.github/workflows/daily.yml`
- 现象：当前 `QUALITY_CHECK_FAIL_OPEN=1`，质量缺陷不会阻断发布。
- 业务约束：必须“有内容产出”，不能因为质检失败断更。
- 建议：保持 fail-open，但引入分级降级兜底（自动补标题/摘要回退/非 AI 剔除）并追加告警与“待复核”标记。

---

- 当前状态：`OPEN`
- 下一步：优先修复 1 → 2 → 3
