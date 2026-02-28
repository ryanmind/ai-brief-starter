# X 官方 API 接入与 `X_BEARER_TOKEN` 获取（详细步骤）

适用项目：`ai-brief-starter`  
目的：让 `sources.txt` 里的 `https://x.com/<账号>` 使用 **官方 X API** 抓取最新动态，保证“严格最新 + 可追溯”。

---

## 1) 先明确：为什么要做这件事

- 作用 1：用官方 API 拉数据，来源可追溯到官方账号原帖。
- 作用 2：减少第三方镜像不稳定问题（延迟、缺失、失效）。
- 作用 3：与本项目严格模式一致（默认 `STRICT_X_API_REQUIRED=1`）。

---

## 2) 是否要钱（截至 2026-02-28）

根据 X 官方文档，X API 当前是 **按量计费（Pay-per-usage）**：

- 你需要在 Developer Console 购买 credits 才能持续调用。
- 没有强制包月承诺（文档写的是 no subscriptions / no commitments）。
- 具体每个 endpoint 的单价，以控制台实时显示为准。
- 如果你是历史 Basic/Pro 用户，文档说明可在控制台选择是否切换到按量计费。

结论：**一般场景下需要付费**（至少要有可用 credits）。

---

## 3) 第一步步操作：开通与拿到 `X_BEARER_TOKEN`

### Step 1. 登录 Developer Console

- 操作：打开 `https://console.x.com`，用你的 X 账号登录。
- 目的：进入开发者平台，后续创建 App 和生成凭证都在这里。

### Step 2. 完成开发者账户开通

- 操作：按页面提示接受开发者协议、补全用途信息。
- 目的：没有开发者权限就无法创建 App，也拿不到 API 凭证。

### Step 3. 创建 App

- 操作：在 Console 里点击 `New App`（或进入已有 App）。
- 目的：`Bearer Token` 是绑定在某个 App 下的，不是账号全局凭证。

### Step 4. 进入 Keys and tokens

- 操作：打开该 App 的 `Keys and tokens` 页面。
- 目的：这里可以查看/复制 `Bearer Token`、API Key、API Secret 等。

### Step 5. 复制 `Bearer Token`

- 操作：复制 `Bearer Token` 并立即安全保存（密码管理器/密钥管理平台）。
- 目的：项目读取这个值作为 `Authorization: Bearer ...` 的认证凭据。
- 注意：如果丢失或泄露，使用 `Regenerate`，旧 token 会失效。

---

## 4) 在本项目中配置（本地 + GitHub Actions）

### A. 本地运行配置

```bash
export X_BEARER_TOKEN='你的真实token'
```

目的：本地运行 `python main.py` 时，脚本能调用官方 X API 拉取账号动态。

### B. GitHub Actions 配置

1. 进入仓库：`Settings -> Secrets and variables -> Actions`  
2. 点击 `New repository secret`  
3. Name 填：`X_BEARER_TOKEN`  
4. Secret 填：你的 Bearer Token  
5. 保存

目的：定时任务里也能安全使用 token，不把凭证写进代码仓库。

---

## 5) 如何验证是否配置成功

### 验证 1：直接调用官方接口（最快）

```bash
curl "https://api.x.com/2/users/by/username/xdevelopers" \
  -H "Authorization: Bearer $X_BEARER_TOKEN"
```

- 成功：返回 JSON（包含 `data.id`/`data.username`）。
- 失败：通常是 token 无效、权限不足、余额/计费问题或网络问题。

### 验证 2：跑本项目主流程

```bash
python main.py
```

- 若 `sources.txt` 有 `x.com` 账号但未配置 token，默认会报错退出（这是预期保护）。
- 生成后的 `reports/latest.md` 应能看到 `x.com/<账号>/status/<id>` 的官方链接。

---

## 6) 与本项目相关的关键环境变量

- `X_BEARER_TOKEN`：官方 X API Bearer Token（核心）
- `STRICT_X_API_REQUIRED`：默认 `1`  
  - `1`：有 X 来源但没 token 就失败（推荐）
  - `0`：没 token 时跳过 X（不推荐，时效与覆盖会下降）
- `X_API_PER_HANDLE`：每个账号拉取条数（默认 `8`）

---

## 7) 常见问题

### Q1：我不想为 X API 付费怎么办？

- 方案 A：从 `sources.txt` 删除所有 `https://x.com/...` 源；
- 方案 B：设 `STRICT_X_API_REQUIRED=0`（会跳过 X，非严格模式）。

### Q2：为什么明明有 token 还报错？

常见原因：
- token 过期或已被 regenerate；
- App 权限/账户状态异常；
- credits 不足或达到消费限制；
- 请求频率或接口配额受限。

---

## 8) 官方参考（建议收藏）

- Getting Access: https://docs.x.com/x-api/getting-started/getting-access
- Pricing: https://docs.x.com/x-api/getting-started/pricing
- Bearer Tokens: https://docs.x.com/fundamentals/authentication/oauth-2-0/bearer-tokens
- First Request: https://docs.x.com/x-api/getting-started/make-your-first-request

---

## 9) 你在中国内地 + 只有万事达卡，是否可行（截至 2026-02-28）

结论：**有机会成功，但不能保证**。  
核心不在“万事达卡本身”，而在“地区支持 + 支付风控 + 账号状态”。

### 9.1 快速判断清单（按顺序做）

1. 能打开并登录 `https://console.x.com`。  
   - 作用：确认账号可进入开发者体系。
2. 在控制台完成 Developer 开通并创建 App。  
   - 作用：拿到 `Keys and tokens` 页面。
3. 尝试购买最小额度 credits（用万事达卡）。  
   - 作用：这是是否能真实用 API 的关键门槛。
4. 拿 token 后跑一次验证请求（见第 5 节）。  
   - 作用：确认不是“可支付但接口不可用”。

### 9.2 为什么会不通过

- X Developer Agreement 要求：你需要在 X 支持该付费服务的国家/地区，并且当地法律允许。  
- X 有权按地区/风控拒绝交易或停止付费服务。  
- 你的发卡行可能拒绝跨境/数字服务交易（常见 3DS、MCC、风控拦截）。

这几条都不是代码问题，属于平台与支付层限制。

---

## 10) 还会遇到哪些问题（建议提前记录）

### 10.1 账号与计费侧

- 购买失败/扣款失败：发卡行拦截、风控、余额或限额不足。
- token 失效：手动 regenerate 后旧 token 立即失效。
- credits 用尽：接口开始报错或不可用。

### 10.2 API 调用侧

- 429 限流：超过 endpoint 限额会被限流，直到窗口重置。
- 401/403：token 无效、权限不足、App 配置问题。
- 结果为空：账号最近无新帖、查询条件过窄、时间窗内无数据。

### 10.3 业务与合规侧（很重要）

- 不能把 X 内容当“原始数据包”随意再分发；分发给第三方有严格限制。  
- 不要做“付费刷互动/买点赞转发”等行为，政策禁止。  
- 对外展示时需保留来源归属（X 为内容来源）。

---

## 11) 做了这套之后，怎么变现（且不踩政策）

下面是对你这个项目最可落地的路径（先从轻量做起）：

### 路径 A：付费简报订阅（推荐先做）

- 产品：每天/每周 AI 早报（中文、结构化、可追溯链接）。  
- 收费：月订阅（个人版/团队版）。  
- 价值：你卖的是“筛选 + 摘要 + 解读 + 时效”，不是卖原始 X 数据。

### 路径 B：企业定制监控

- 产品：按行业/竞品/技术栈定制信源与告警。  
- 收费：按月服务费 + 定制费。  
- 价值：省去企业内部信息检索人力成本。

### 路径 C：社群增值服务

- 产品：微信群/飞书群每日卡片 + 周报深度点评。  
- 收费：社群会员费或课程打包。  
- 价值：高频触达 + 可执行建议。

### 变现时要守的边界

- 以“分析结论 + 原文链接”交付，不做大规模原文搬运/数据再分销。  
- 不承诺“完整 X 全量数据”，而是承诺“高质量追踪与可追溯”。  
- 在服务条款里写明：数据来源于公开官方渠道，受平台规则约束。

---

## 12) 成本怎么控（实操版）

### 12.1 先建一个成本公式

每月 API 成本 ~= 各 endpoint 调用次数 × 对应单价（控制台实时价格）  

你至少要每周看一次控制台的 Usage + Credits 变化，避免月底超支。

### 12.2 在本项目里可直接用的降本开关

- 减少 X 账号数量（`sources.txt` 中 `x.com` 条目）。
- 下调 `X_API_PER_HANDLE`（默认 8，可先降到 3-5）。
- 降低任务频率（先每日 1 次，再按订阅规模提高）。
- 保持 `TOP_N` 在 20 左右，不盲目扩大。
- 开启严格一手过滤，减少低价值条目进入后续处理成本。

### 12.3 建议的预算防线

1. 设月预算上限（例如先从小额 credits 起步）。  
2. 设预警线（50%/80%/95%）并通知到飞书或邮件。  
3. 达到 80% 后自动降级策略：  
   - 减账号数  
   - 减每账号抓取条数  
   - 降频率

### 12.4 如何做使用量监控

官方给了 Usage API，可程序化监控消耗（见 Pricing 页面示例）。  
你可以把它接到定时脚本，每天生成一份“用量 + 预计剩余天数”报告。

---

## 13) 相关官方条款（建议务必读一遍）

- X Developer Agreement: https://docs.x.com/developer-terms/agreement
- X API Pricing: https://docs.x.com/x-api/getting-started/pricing
- X API Rate Limits: https://docs.x.com/x-api/fundamentals/rate-limits
- Bearer Token: https://docs.x.com/fundamentals/authentication/oauth-2-0/bearer-tokens
