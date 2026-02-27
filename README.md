# AI Brief Starter

这个目录可直接迁移为独立仓库使用。

## 快速开始

1. 配置 GitHub Actions Secrets
   - 必需：`QWEN_API_KEY`
   - 可选：`KIMI_API_KEY`
2. 推送代码到 GitHub（建议 private 仓库）
3. 在 Actions 里手动运行 `ai-morning-brief`
4. 查看 `reports/latest.md`

## 目录

- `PRD.md`：需求文档
- `main.py`：采集 + 摘要 + 生成早报
- `sources.txt`：RSS 来源
- `.github/workflows/daily.yml`：定时任务
- `reports/`：日报输出

## 说明

- 默认只用 Qwen；配置 `KIMI_API_KEY` 后才会启用 Kimi 精修。
- 当前版本不包含企业微信通知。
- `sources.txt` 可直接写 `https://x.com/<账号>`，脚本会自动转成 Nitter RSS（可用 `NITTER_RSS_BASE` 覆盖默认域名）。
