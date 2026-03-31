---
title: 首页
description: AI 资讯自动快讯生成器
hide:
  - navigation
---

# AI Brief Starter

<div class="result" markdown>

自动化抓取 → AI 过滤排序 → 中文本地化 → 定时推送发布

</div>

## 功能特性

<div class="grid cards" markdown>

-   :material-autorenew: **自动化抓取**
    多来源支持：RSS / X (Twitter) / GitHub Releases / GitHub Trending，每日自动运行

-   :material-brain: **AI 智能处理**
    LLM 驱动的内容过滤、排名摘要、事实核查、多模型交叉审核

-   :material-translate: **中文本地化**
    自动翻译并润色为中文，保持口语化专业风格

-   :material-bell: **多渠道通知**
    支持飞书群机器人、Server酱微信推送

-   :material-book-open-variant: **文档站归档**
    自动同步至 GitHub Pages，形成可搜索的历史知识库

-   :material-shield-check: **质量保障**
    多模型投票审核、SSRF 防护、路径遍历防护、敏感词过滤

</div>

## 快速上手

```bash
git clone https://github.com/ryanmind/ai-brief-starter.git
cd ai-brief-starter
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export QWEN_API_KEY="your-key"
python main.py
```

[快速开始 →](quick-start.md){ .md-button .md-button--primary }
[查看最新快讯 →](latest.md){ .md-button }

---

**开源免费 · 每日自动运行 · 无需值守**
