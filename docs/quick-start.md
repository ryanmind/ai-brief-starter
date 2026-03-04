# 快速开始

本指南帮助你在 5 分钟内运行起 AI 早报生成器。

## 本地运行

### 1. 克隆仓库

```bash
git clone https://github.com/ryanmind/ai-brief-starter.git
cd ai-brief-starter
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API Key

```bash
export QWEN_API_KEY="sk-xxxxxx"  # 阿里百炼 API Key
```

### 5. 运行

```bash
python main.py
```

输出文件：
- `reports/latest.md` - 最新早报
- `reports/YYYY-MM-DD.md` - 按日期归档

---

## GitHub Actions 自动化

### 1. 配置 Secrets

进入 GitHub 仓库 `Settings` → `Secrets and variables` → `Actions`：

| Secret | 必需 | 说明 |
|--------|------|------|
| `QWEN_API_KEY` | ✅ | 阿里百炼 API Key |
| `FEISHU_WEBHOOK_URL` | ❌ | 飞书群机器人 Webhook |
| `FEISHU_APP_ID` | ❌ | 飞书应用 ID |
| `FEISHU_APP_SECRET` | ❌ | 飞书应用密钥 |

### 2. 手动触发

1. 进入 `Actions` 标签页
2. 选择 `ai-morning-brief` 工作流
3. 点击 `Run workflow`

### 3. 自动定时

工作流已配置北京时间每天 07:30 自动运行：

```yaml
schedule:
  - cron: "30 23 * * *"  # UTC 23:30 = Beijing 07:30
```

---

## 常见问题

### Q: 运行失败提示缺少 QWEN_API_KEY

确保已在 GitHub Secrets 中配置 `QWEN_API_KEY`。

### Q: 如何获取阿里百炼 API Key？

1. 访问 [阿里百炼](https://bailian.console.aliyun.com/)
2. 开通服务
3. 创建 API Key

### Q: 如何添加新的信息源？

编辑 `sources.txt`，每行一个 RSS 链接：

```
https://example.com/feed.xml
https://x.com/username
https://github.com/owner/repo/releases.atom
```
