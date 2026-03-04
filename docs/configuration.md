# 环境变量配置

所有配置项都通过环境变量控制，可在 GitHub Actions 中设置或本地 export。

## 必需配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `QWEN_API_KEY` | 阿里百炼 API Key | `sk-xxxxxx` |

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

---

## 过滤配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `STRICT_PRIMARY_ONLY` | `1` | 开启一手来源过滤 |
| `STRICT_AI_TOPIC_ONLY` | `1` | 开启 AI 主题过滤 |
| `AI_TOPIC_KEYWORDS` | 见下方 | AI 主题关键词 |
| `PRIMARY_SOURCE_DOMAINS` | 见下方 | 一手来源域名白名单 |
| `PRIMARY_X_HANDLES` | 见下方 | 一手 X 账号白名单 |
| `SECOND_HAND_DOMAINS` | 见下方 | 二手媒体域名黑名单 |

### AI 主题关键词（默认）

```
AI, 人工智能, 机器学习, 深度学习, LLM, 大模型, GPT, Claude, 
OpenAI, Anthropic, Gemini, Qwen, 通义, 文心, Midjourney, 
Stable Diffusion, 生成式, AIGC, AGI, AI Agent, 智能体
```

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

| 变量名 | 说明 |
|--------|------|
| `FEISHU_WEBHOOK_URL` | 飞书群机器人 Webhook |
| `FEISHU_BOT_SECRET` | 机器人签名密钥 |
| `FEISHU_APP_ID` | 飞书应用 ID |
| `FEISHU_APP_SECRET` | 飞书应用密钥 |
| `FEISHU_REPORT_FOLDER_TOKEN` | 归档文件夹 Token |
| `FEISHU_REPORT_DOC_URL` | 总览文档链接 |
| `FEISHU_DOC_SYNC_REQUIRED` | `1` 是否必须同步文档 |
| `FEISHU_DOC_PUBLIC_READABLE` | `1` 文档是否公开可读 |
| `FEISHU_DOC_PUBLIC_REQUIRED` | `1` 是否必须公开 |

---

## 其他配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `NITTER_RSS_BASES` | 多个实例 | Nitter RSS 实例列表 |
| `FINAL_POLISH_ENABLED` | `1` | 开启最终润色 |
