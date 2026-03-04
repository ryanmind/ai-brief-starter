# TwitterAPI.io 作为 X 数据源 Fallback（评估结论）

> 最后核验时间：2026-03-04（北京时间）

## 结论（是否合适）

**合适，但建议仅作为 Nitter 失败时的兜底来源，不建议直接替代全部 X 抓取链路。**

原因：

1. 对本项目当前调用规模，成本低且可控。  
2. 现有架构可小改接入，风险较低。  
3. 但它是第三方服务，需关注条款/合规与稳定性风险。

## 关键事实（已更正）

### TwitterAPI.io

- 官方站点：https://twitterapi.io/
- 官方文档：https://docs.twitterapi.io/
- 定价页：https://twitterapi.io/pricing

按官方说明（2026-03-04 核验）：

- 核心为 **Credits 按量计费**（也可选月度自动充值方案）。
- **1 USD = 100,000 credits**。
- `GET /twitter/user/last_tweets` 端点：**15 credits / tweet**，且 **最低 15 credits / request**。

> 旧版文档中“100,000 条推文/月免费额度”表述不准确，应删除。

### X 官方 API（用于对比）

- 定价入口：https://docs.x.com/x-api/getting-started/pricing

按官方页面（2026-03-04 核验）可见：

- 当前主模式为 **Pay-per-usage**（信用点预充值、按端点计费）。
- Basic / Pro 属于 **legacy 订阅路径**（旧方案迁移说明仍在页面可见）。

> 因 X 定价模型变动频繁，本文仅做决策参考，最终以 Developer Console 当日价格为准。

## 本项目成本估算（按当前仓库）

### 当前参数（来自仓库）

- `sources.txt` 中 X 账号：约 **20** 个
- 定时任务：每天 1 次（`.github/workflows/daily.yml`）
- `PER_SOURCE_ITEMS=30`

### 上限测算（假设每次 fallback 都触发且每账号拿满 30 条）

- 每日推文：20 × 30 = **600**
- 每月推文：600 × 30 = **18,000**
- Credits：18,000 × 15 = **270,000 credits**
- 成本：270,000 / 100,000 = **$2.70 / 月**

### 说明

- 如果仅在 Nitter 失败时才触发，实际成本通常低于上限。
- 若改为高频轮询（例如每小时/每 5 分钟），成本会显著上升。

## 接入方案建议

### 推荐：方案 A（仅做 Fallback）

保持当前主链路：

```text
sources.txt (x.com 账号)
    ↓
expand_source_urls() -> Nitter RSS URL
    ↓
probe_nitter_bases() -> 探测可用实例
    ↓
_fetch_single_source() -> feedparser 抓取
    ↓ 失败
TwitterAPI.io API (fallback)
```

### 预计改动

- `src/config.py`
  - 新增：`TWITTERAPI_IO_KEY`
  - 可选：`TWITTERAPI_IO_ENABLED`、`TWITTERAPI_IO_TIMEOUT`
- `main.py`
  - 新增：`fetch_from_twitterapi_io()`
  - 在 `_fetch_single_source()` 或 X 源抓取分支中添加 fallback
- `.github/workflows/daily.yml`
  - 新增 secret：`TWITTERAPI_IO_KEY`
- `requirements.txt`
  - 无需新增（已存在 `requests`）

### 不建议：方案 B（完全替换）

除非你明确决定放弃 Nitter 生态，否则不建议一次性替换：

- 迁移成本更高
- 第三方供应商锁定更强
- 成本暴露更直接

## 风险与控制

- 合规风险：第三方数据服务条款可能调整，建议在仓库文档中明确“仅用于公开信息聚合”。
- 稳定性风险：第三方 API 也可能抖动，需保留“失败回退 + 降级跳过”。
- 成本风险：建议增加日成本监控（请求数、返回条数、估算 credits）。
- 运维建议：提供开关（如 `TWITTERAPI_IO_ENABLED`），便于一键停用。

## 最终判断

**适合接入，前提是“仅作为 fallback + 加上成本与合规防护”。**

这样可以在 Nitter 不稳定时提升成功率，同时把新增成本控制在低位。

## 参考链接

- TwitterAPI.io 首页：https://twitterapi.io/
- TwitterAPI.io 文档：https://docs.twitterapi.io/
- TwitterAPI.io 定价：https://twitterapi.io/pricing
- TwitterAPI.io User Last Tweets 端点：https://docs.twitterapi.io/docs/twitter-user-last-tweets
- X API 定价：https://docs.x.com/x-api/getting-started/pricing
