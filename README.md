# AI Brief Starter

AI 资讯自动早报生成器 —— 每天 07:30 自动生成 AI 行业早报，推送至飞书。

📚 **[在线文档](https://ryanmind.github.io/ai-brief-starter/)**

## 快速开始

1. 配置 GitHub Actions Secrets
   - 必需：`QWEN_API_KEY`
   - 推送通知（二选一或同时配置）：
     - 飞书：`FEISHU_WEBHOOK_URL`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`
     - 微信：`SERVERCHAN_SENDKEY`
2. 推送代码到 GitHub（建议 private 仓库）
3. 在 Actions 里手动运行 `ai-morning-brief`
4. 在飞书或微信查看通知，或在 Actions 下载 `ai-brief-reports` artifact

## 微信推送配置（Server酱）

每天早报生成后自动推送到微信，方便转发朋友圈/小红书。

### 获取 SendKey

1. 访问 https://sct.ftqq.com/
2. 微信扫码登录
3. 复制你的 **SendKey**

### 配置 GitHub Secret

在仓库 `Settings` → `Secrets and variables` → `Actions` 添加：

| Secret 名称 | 值 |
|------------|-----|
| `SERVERCHAN_SENDKEY` | 你的 SendKey |

配置后，每天早报生成完成会收到微信消息，可直接复制转发。

## 配置 QWEN_API_KEY（6步）

1. 打开你的 GitHub 仓库页面。
2. 进入 `Settings`。
3. 左侧点击 `Secrets and variables` -> `Actions`。
4. 点击 `New repository secret`。
5. `Name` 填写 `QWEN_API_KEY`。
6. `Secret` 填入阿里百炼 API Key（`sk-...`），点击 `Add secret`。

## 首次运行检查（避免常见坑）

- 仓库默认分支要和你实际使用的分支一致（当前示例为 `master`），`schedule` 只会在默认分支触发。
- 工作流会回写 `docs/latest.md`、`docs/history/**`，并提交最新的 `reports/*.md` 产物，因此 `ai-morning-brief` 需要 `contents: write`。
- 必须配置 `QWEN_API_KEY`，未配置会在工作流里直接报错并停止。

## 目录

- `main.py`：采集 + 摘要 + 生成早报
- `sources.txt`：RSS 来源
- `scripts/`：辅助脚本（飞书通知、质量检查、源健康检查）
- `src/config.py`：配置常量
- `tests/`：单元测试
- `reports/`：运行时产物目录（CI 会提交最新 `latest.md` 与按日期归档报告）
- `docs/`：MkDocs 文档源文件
- `mkdocs.yml`：MkDocs 配置文件
- `PRD.md`：需求文档
- `TEMPLATE.md`：早报模板标准文件

## 文档站点

本项目使用 MkDocs + GitHub Pages 托管文档：

- **在线文档**：https://ryanmind.github.io/ai-brief-starter/
- **源文件**：`docs/` 目录
- **本地预览**：`mkdocs serve`

详见 `docs/mkdocs-tutorial.md` 搭建教程。
