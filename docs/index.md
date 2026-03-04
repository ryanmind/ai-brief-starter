# AI Brief Starter

AI 资讯自动早报生成器 —— 每天 07:30 自动生成 AI 行业早报，推送至飞书。

## ✨ 核心特性

- 🤖 **智能摘要** - 使用 Qwen 大模型自动筛选、打分、生成摘要
- 📰 **多源聚合** - 支持 RSS、Twitter/X、GitHub 等多种信息源
- 🔍 **一手过滤** - 自动识别并过滤二手转述内容
- 📅 **跨天去重** - 避免重复推送相同资讯
- 📤 **飞书集成** - 自动推送群通知 + 创建飞书文档

## 🚀 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/ryanmind/ai-brief-starter.git
cd ai-brief-starter

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
export QWEN_API_KEY="your-api-key"

# 4. 运行
python main.py
```

[查看完整配置指南 →](quick-start.md)

## 📖 文档目录

| 文档 | 说明 |
|------|------|
| [快速开始](quick-start.md) | 本地运行与 GitHub Actions 配置 |
| [环境变量](configuration.md) | 所有可配置参数详解 |
| [信息源配置](sources.md) | RSS、Twitter、GitHub 源配置 |
| [飞书集成](feishu-sync.md) | 飞书群通知与文档同步 |
| [早报模板](template.md) | 输出格式说明 |
| [产品需求](prd.md) | PRD 文档 |

## 🏗️ 项目结构

```
ai-brief-starter/
├── main.py              # 主程序入口
├── sources.txt          # 信息源列表
├── src/config.py        # 配置常量
├── scripts/             # 辅助脚本
│   ├── notify_feishu.py
│   ├── report_quality_check.py
│   └── source_health_check.py
├── tests/               # 单元测试
├── reports/             # 输出目录
└── .github/workflows/   # GitHub Actions
```

## 📄 许可证

MIT License
