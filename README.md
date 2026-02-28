# AI Brief Starter

这个目录可直接迁移为独立仓库使用。

## 快速开始

1. 配置 GitHub Actions Secrets
   - 必需：`QWEN_API_KEY`
   - 可选：`KIMI_API_KEY`
2. 推送代码到 GitHub（建议 private 仓库）
3. 在 Actions 里手动运行 `ai-morning-brief`
4. 查看 `reports/latest.md`

## 配置 QWEN_API_KEY（6步）

1. 打开你的 GitHub 仓库页面。
2. 进入 `Settings`。
3. 左侧点击 `Secrets and variables` -> `Actions`。
4. 点击 `New repository secret`。
5. `Name` 填写 `QWEN_API_KEY`。
6. `Secret` 填入阿里百炼 API Key（`sk-...`），点击 `Add secret`。

## 首次运行检查（避免常见坑）

- 仓库默认分支要和你实际使用的分支一致（当前示例为 `master`），`schedule` 只会在默认分支触发。
- 仓库设置需允许工作流写回仓库：`Settings -> Actions -> General -> Workflow permissions -> Read and write permissions`。
- 必须配置 `QWEN_API_KEY`，未配置会在工作流里直接报错并停止。

## 目录

- `PRD.md`：需求文档
- `main.py`：采集 + 摘要 + 生成早报
- `sources.txt`：RSS 来源
- `.github/workflows/daily.yml`：定时任务
- `reports/`：日报输出

## 说明

- 默认只用 Qwen；配置 `KIMI_API_KEY` 后才会启用 Kimi 精修。
- 当前版本不包含企业微信通知。
- 当前版本仅输出中文早报。
- `sources.txt` 可直接写 `https://x.com/<账号>`，脚本会自动转成 Nitter RSS（可用 `NITTER_RSS_BASES` 配置多个实例，逗号分隔）。
