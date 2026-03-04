# 环境变量配置

所有配置项都通过环境变量控制，可在 GitHub Actions 中设置或本地 `export`。
默认值主要来自 `src/config.py` 与 `.github/workflows/daily.yml`。

## 必需配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `QWEN_API_KEY` | 阿里百炼 API Key | `sk-xxxxxx` |
| `TWITTERAPI_IO_KEY` | （可选）TwitterAPI.io API Key，用于 X 源 fallback | `taio-xxxxxx` |

---

## 模型配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `QWEN_MODEL` | `qwen-flash` | Qwen 模型名称 |
| `MAX_ITEMS` | `120` | 最大抓取条数 |
| `TOP_N` | `20` | 最终输出条数 |

---

## 内容长度控制

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `BRIEF_MAX_CHARS` | `160` | 摘要最大字符数 |
| `DETAIL_MAX_CHARS` | `260` | 详情最大字符数 |
| `DETAIL_MIN_CHARS` | `48` | 详情最小字符数 |
| `IMPACT_MAX_CHARS` | `140` | 影响分析最大字符数 |
| `KEY_POINT_MAX_CHARS` | `28` | 关键点最大字符数 |
| `KEY_POINTS_MIN_COUNT` | `2` | 关键点最小数量 |
| `KEY_POINTS_MAX_COUNT` | `3` | 关键点最大数量 |

---

## 抓取配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `FETCH_HOURS` | `24` | 抓取时间窗口（小时） |
| `FALLBACK_FETCH_HOURS` | `72` | 条目不足时扩展窗口 |
| `PER_SOURCE_ITEMS` | `30` | 单源最大抓取条数 |
| `PER_DOMAIN_LIMIT` | `4` | 单域名最大输出条数 |
| `ARXIV_MAX_ITEMS` | `4` | arXiv 来源最大条数 |
| `TWITTERAPI_IO_ENABLED` | `0` | 启用 TwitterAPI.io 作为 X 源 fallback |
| `TWITTERAPI_IO_TIMEOUT` | `8` | TwitterAPI.io 请求超时（秒） |
| `TWITTERAPI_IO_BASE_URL` | `https://api.twitterapi.io` | TwitterAPI.io API 基础地址 |

---

## 过滤配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `STRICT_PRIMARY_ONLY` | `1` | 开启一手来源过滤 |
| `STRICT_AI_TOPIC_ONLY` | `1` | 开启 AI 主题过滤 |
| `AI_TOPIC_KEYWORDS` | 见下方 | AI 主题关键词 |
| `AI_TOPIC_LLM_BATCH_SIZE` | `24` | AI 主题 LLM 判定批大小 |
| `PRIMARY_SOURCE_DOMAINS` | 见下方 | 一手来源域名白名单 |
| `PRIMARY_X_HANDLES` | 见下方 | 一手 X 账号白名单 |
| `SECOND_HAND_DOMAINS` | 见下方 | 二手媒体域名黑名单 |

### AI 主题关键词（默认）

以下为当前代码默认值（以 `src/config.py` 为准）：

```
ai, artificial intelligence, machine learning, deep learning, llm,
gpt, chatgpt, rag, agent, agentic, multimodal, diffusion, transformer,
inference, fine-tuning, fine tuning, 模型, 大模型, 智能体, 多模态,
推理, 训练, 微调, 生成式, 开源权重, openai, anthropic, deepmind,
mistral, qwen, deepseek, hunyuan, moonshot, kimi, gemini, llama,
claude, codex, arxiv
```

> 说明：当前 AI 主题过滤以 LLM 判定为主，`AI_TOPIC_KEYWORDS` 用作模型提示词辅助，不再作为硬规则子串过滤。

---

## 去重配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `HISTORY_DEDUP_DAYS` | `2` | 跨天去重天数 |
| `HISTORY_STATE_PATH` | `reports/history_index.json` | 去重索引文件路径 |
| `HISTORY_STATE_MAX_DAYS` | `14` | 索引保留天数 |

---

## 质量控制

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `STRICT_FACT_MODE` | `1` | 开启事实保守模式 |
| `FACT_OVERLAP_MIN` | `0.55` | 事实重合阈值 |
| `QUALITY_CHECK_STRICT` | `1` | 开启严格质检 |
| `QUALITY_CHECK_FAIL_OPEN` | `1` | 质检失败是否继续发布 |
| `TITLE_COMPLETE_RATIO_MIN` | `0.90` | 标题完整率阈值 |

---

## 飞书配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `FEISHU_WEBHOOK_URL` | 空 | 飞书群机器人 Webhook |
| `FEISHU_BOT_SECRET` | 空 | 机器人签名密钥 |
| `FEISHU_APP_ID` | 空 | 飞书应用 ID |
| `FEISHU_APP_SECRET` | 空 | 飞书应用密钥 |
| `FEISHU_REPORT_FOLDER_TOKEN` | 空 | 归档文件夹 Token |
| `FEISHU_REPORT_DOC_URL` | 空 | 飞书总览文档链接 |
| `FEISHU_DOC_SYNC_REQUIRED` | `1` | 是否必须同步文档后再发送飞书消息 |
| `FEISHU_DOC_PUBLIC_READABLE` | `1` | 文档是否公开可读 |
| `FEISHU_DOC_PUBLIC_REQUIRED` | `1` | 是否强制公开可读，不满足则报错 |

> 当前默认配置下，若设置了 `FEISHU_WEBHOOK_URL` 但缺少 `FEISHU_APP_ID`/`FEISHU_APP_SECRET`，飞书通知步骤会失败。

---

## 微信配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SERVERCHAN_SENDKEY` | 空 | Server酱 SendKey，用于微信推送 |

---

## 其他配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `NITTER_RSS_BASES` | 多个实例 | Nitter RSS 实例列表 |
| `FINAL_POLISH_ENABLED` | `1` | 开启最终润色 |
| `TZ` | `Asia/Shanghai` | 工作流时区 |
