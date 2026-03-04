# Agent 集群与 3-Agent 改造思路

本文记录两个目标：

1. 统一说明什么是 Agent 集群；
2. 给出本项目从“单体流水线”升级到“3-Agent 协作”时，具体该改哪些地方。

## 什么是 Agent 集群

Agent 集群可以理解为：由多个角色化 Agent 组成的协作系统。  
每个 Agent 只负责一类能力（例如采集、写作、质检），由调度层把它们串成一个可回放、可重试、可评估的流程。

和“单个大 prompt 一次出结果”相比，Agent 集群更适合：

- 多步骤任务（抓取 -> 筛选 -> 生成 -> 质检）；
- 需要稳定输出格式的任务；
- 需要定位问题来源（是哪一步出错）的任务。

## 为什么 AI Brief Starter 值得做 3-Agent

当前 `main.py` 已经覆盖了抓取、过滤、摘要、渲染、质检等完整链路，功能很强，但职责集中在单文件中。  
引入 3-Agent 的核心收益不是“更炫”，而是：

- 职责更清晰：每个 Agent 只管一个阶段；
- 质量更稳定：质检 Agent 可独立否决或重写问题条目；
- 迭代更快：后续替换模型、调 prompt、加新源时，影响面更小。

## 推荐的 3-Agent 角色划分

### Agent 1：Scout（侦察/采集）

职责：

- 读取 `sources.txt`，抓取 RSS/X/GitHub；
- 做基础清洗、去重、时效过滤；
- 过滤明显二手或非 AI 主题内容；
- 产出 `candidate_items`（只保留事实字段，不写“观点”）。

可复用现有能力（`main.py`）：

- `fetch_items`
- `filter_primary_items_with_stats`
- `filter_ai_topic_items_with_stats`
- `apply_source_limits`
- 历史去重相关函数（`filter_items_by_history` 等）

### Agent 2：Analyst（分析/生成）

职责：

- 对候选内容排序、打分；
- 生成标题、摘要、关键要点、影响分析；
- 进行中文化与风格统一；
- 输出结构化 `draft_items`。

可复用现有能力（`main.py`）：

- `rank_and_summarize`
- `localize_items_to_chinese`
- `enforce_titles_with_subject`
- `finalize_key_points`

### Agent 3：Reviewer（审校/质检）

职责：

- 事实一致性检查（数字、链接、表述重叠度）；
- 模板结构检查（是否满足 `TEMPLATE.md` 要求）；
- 对低质量条目进行回退（extractive/fallback）；
- 决定是否允许进入最终渲染。

可复用现有能力（`main.py` + `scripts/`）：

- `sanitize_items_factuality`
- `fix_items_detail`
- `polish_markdown_with_llm`
- `scripts/report_quality_check.py`

## 改造时“先改什么”

建议按“最小可用改造”推进，而不是一次性重写。

### Phase 0（低风险）：先包一层 Orchestrator

- 新增 `src/agents/orchestrator.py`；
- `main.py` 只保留入口和 I/O，调用 `orchestrator.run()`；
- 先不改变算法逻辑，只把现有函数按阶段组织起来。

验收标准（Done）：

- `python main.py` 输出内容与改造前在结构上保持兼容；
- 关键指标（条目数、失败率、执行时长）波动在可接受范围；
- 不改动 `TEMPLATE.md` 的前提下，`report_quality_check.py` 通过。

### Phase 1（核心）：拆 3 个 Agent 模块

建议目录：

```text
src/agents/
  __init__.py
  schemas.py
  scout_agent.py
  analyst_agent.py
  reviewer_agent.py
  orchestrator.py
```

- `schemas.py`：统一 `RawItem / CandidateItem / DraftItem / FinalItem` 数据结构；
- 每个 Agent 暴露 `run(...)`，输入输出固定；
- 将 prompt 文本从 `main.py` 移入 Agent 模块，降低耦合。

验收标准（Done）：

- 3 个 Agent 均可单测独立运行；
- Orchestrator 中可插拔执行（允许跳过某个 Agent）；
- 旧流程对外接口保持不变（仍生成 `reports/latest.md`）。

### Phase 2（增强）：可观测与回放

- 在 `reports/` 增加中间产物：
  - `agent_trace.json`
  - `candidates.json`
  - `drafts.json`
- 失败时能定位是 Scout/Analyst/Reviewer 哪一步造成；
- 为每个 Agent 增加耗时、通过率、回退率指标。

验收标准（Done）：

- 任意失败任务可通过 `agent_trace.json` 追溯到具体阶段；
- CI/本地日志可看到每个 Agent 的耗时与结果状态；
- 回退策略可触发且结果可验证（如 Reviewer 否决后 fallback 生效）。

## 配置层建议（`src/config.py`）

新增分 Agent 配置，避免单一全局参数难调优：

- `SCOUT_MODEL`
- `ANALYST_MODEL`
- `REVIEWER_MODEL`
- `AGENT_MAX_RETRIES`
- `AGENT_TIMEOUT_SECONDS`

说明：参数默认可保持与现有模型一致，先保证行为兼容，再逐步细调。

## 数据契约示例（`schemas.py`）

建议先用 `dataclass` 或 `TypedDict` 固化最小字段，避免 Agent 之间“口头协议”。

```python
from dataclasses import dataclass, field

@dataclass
class RawItem:
    source: str
    title: str
    url: str
    published_at: str = ""
    content: str = ""

@dataclass
class CandidateItem:
    source: str
    title: str
    url: str
    facts: list[str] = field(default_factory=list)
    score_hint: float = 0.0

@dataclass
class DraftItem:
    title: str
    summary: str
    key_points: list[str]
    impact: str
    source: str

@dataclass
class FinalItem:
    title: str
    summary: str
    key_points: list[str]
    impact: str
    source: str
    quality_passed: bool = True
```

最低要求：

- `CandidateItem -> DraftItem -> FinalItem` 字段单向收敛，不允许越级读取原始抓取噪声；
- `source/url` 在所有阶段必须保留，便于事实追溯；
- Reviewer 只修改 `DraftItem`，不回写 `RawItem`。

## 测试改造建议

新增测试重点：

- Agent 间数据契约测试（字段完整、类型稳定）；
- Reviewer 拒绝策略回归测试（事实冲突、弱信息、格式错误）；
- 端到端冒烟测试：3-Agent 流程输出仍可通过 `report_quality_check.py`。

可落地的测试文件示例：

- `tests/test_scout_agent.py`
- `tests/test_analyst_agent.py`
- `tests/test_reviewer_agent.py`
- `tests/test_agent_orchestrator_e2e.py`

## 风险与回滚策略

常见风险：

- 新 Agent 提示词不稳定导致摘要质量波动；
- Agent 间字段不一致导致流程中断；
- 审校过严导致有效条目被大量拒绝。

回滚设计建议：

1. 保留 `LEGACY_PIPELINE=true` 开关，出现异常时走原有单体流程；
2. 引入 `AGENT_MODE=shadow`，先并行跑新旧流程，仅比较结果不对外发布；
3. 对 Reviewer 设置下限保护（例如“至少保留 N 条”），避免全量拒绝。

回滚触发条件（建议）：

- 连续 2 次日报未通过质量检查；
- 条目数低于阈值（如 `< 5`）且非源站故障；
- 关键字段缺失率超过阈值（如 `> 10%`）。

## 一句话落地策略

先“分层不换脑”（先拆结构、尽量复用现有函数），再“局部换脑”（逐步替换各 Agent 的 prompt/模型），最终实现稳定、可诊断、可扩展的 Agent 集群流水线。
