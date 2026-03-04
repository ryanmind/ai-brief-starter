# X API（官方）调研与校正版

> 最后核验时间：2026-03-04（北京时间）

## 结论

这份文档已按当前官方信息校正。核心结论：

1. **X API 当前主模式是 Pay-per-usage（按量付费）**，不是旧版固定订阅为主。  
2. **Basic / Pro 属于 legacy（历史订阅路径）**，是否可选以 Developer Console 页面为准。  
3. 本项目若只做 X 源兜底抓取，优先建议继续采用“RSS/Nitter 主链路 + 付费 API fallback”。

## 官方入口

- 开发者站点：https://docs.x.com/
- X API 介绍：https://docs.x.com/x-api/introduction
- 定价页：https://docs.x.com/x-api/getting-started/pricing
- 关于 X API：https://docs.x.com/x-api/getting-started/about-x-api

## X API 主要能力

| 功能 | 说明 |
|------|------|
| 读取帖子 | 获取公开 Post（原 Tweet）内容 |
| 用户数据 | 查询用户信息、关系与资料 |
| 搜索分析 | 搜索与分析公开对话 |
| 发布内容 | 发帖、回复等写入能力 |
| 其他能力 | Trends、Spaces、Lists、DM（按产品与权限） |

> 具体可用端点与配额依赖你的应用权限与计费状态。

## 计费模式（2026-03-04 核验）

### 当前主模型

- X API 使用 **Pay-per-usage**。
- 以 **Credits 预充值** 方式计费，按端点消耗。
- **无固定月订阅承诺**（no subscriptions / no minimum spend）。

### 重要说明

- 官方明确提到：**legacy subscription（Basic/Pro）仍可见/可切换**，但主推是按量模式。  
- 不同端点单价在 **Developer Console** 动态展示，应以控制台当日价格为准。  
- 官方文档同时提到：pay-per-usage 计划存在 **每月 Post reads 上限（文档写 2M）**，更高需求走 Enterprise。

## 与旧版常见说法的差异（已修正）

以下旧说法不再适合作为当前默认结论：

- “Basic 固定 $100/月、10,000 条读取”
- “Pro 固定 $5,000/月、1,000,000 条读取”
- “Free 仅发帖不能读（绝对化表述）”

这些信息来自历史阶段或旧套餐语境，**不能直接当作 2026 年默认定价事实**。

## 与 TwitterAPI.io 的可比口径

为避免误导，统一按“公开页面可核验事实”对比：

| 项目 | X 官方 API | TwitterAPI.io |
|------|------------|---------------|
| 当前主计费模型 | Pay-per-usage（credits） | Pay-as-you-go（credits） |
| 是否固定月费为主 | 否（主模型） | 否（主模型） |
| 单价展示方式 | 以 Developer Console 端点价格为准 | 官网公开 credits 单价 |
| 备注 | legacy Basic/Pro 仍可见 | 支持充值包/自动充值方案 |

### TwitterAPI.io（用于本项目兜底测算）

- 定价页标注：`1 USD = 100,000 credits`
- Tweets：`15 credits / returned tweet`
- 最低调用成本：`15 credits / request`（bulk 响应可豁免）

在“20 个 X 账号 × 每次 30 条 × 每天 1 次”上限下：

- 约 18,000 tweets / 月
- 约 270,000 credits / 月
- 约 **$2.70 / 月**（上限估算）

## 对本项目的建议

1. 保持当前主链路（RSS/Nitter）不变。  
2. 仅在主链路失败时使用付费 API fallback。  
3. 为 fallback 加开关、超时与成本日志，避免失控。

## 参考链接

- X 定价（官方）：https://docs.x.com/x-api/getting-started/pricing
- X API 介绍（官方）：https://docs.x.com/x-api/introduction
- X API 概览（官方）：https://docs.x.com/
- X API About（官方）：https://docs.x.com/x-api/getting-started/about-x-api
- TwitterAPI.io 定价：https://twitterapi.io/pricing
- TwitterAPI.io 端点示例：https://docs.twitterapi.io/docs/twitter-user-last-tweets
