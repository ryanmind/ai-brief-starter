# MkDocs + GitHub Pages 完整教程

本教程将帮助你在 10 分钟内为项目搭建一个专业的文档站点。

---

## 一、前置要求

- 已有 GitHub 仓库（本项目）
- 本地已安装 Python 3.11+
- 已安装 pip

---

## 二、本地安装与配置

### 2.1 安装依赖

```bash
# 激活虚拟环境（如有）
source .venv/bin/activate

# 安装 MkDocs 及 Material 主题
pip install mkdocs mkdocs-material
```

### 2.2 创建配置文件

在项目根目录创建 `mkdocs.yml`：

```yaml
site_name: AI Brief Starter
site_description: AI 资讯自动早报生成器
site_author: Ryan
site_url: https://your-username.github.io/ai-brief-starter/

# 仓库信息
repo_name: ryanmind/ai-brief-starter
repo_url: https://github.com/ryanmind/ai-brief-starter

# 主题配置
theme:
  name: material
  language: zh
  palette:
    # 明亮模式
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: 切换到暗色模式
    # 暗色模式
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: 切换到亮色模式
  features:
    - navigation.instant      # 即时加载
    - navigation.tracking     # URL 跟踪
    - navigation.tabs         # 顶部导航标签
    - navigation.sections     # 侧边栏分组
    - navigation.expand       # 默认展开侧边栏
    - navigation.top          # 返回顶部按钮
    - search.suggest          # 搜索建议
    - search.highlight        # 搜索高亮
    - content.code.copy       # 代码复制按钮

# Markdown 扩展
markdown_extensions:
  - abbr
  - admonition
  - attr_list
  - def_list
  - footnotes
  - md_in_html
  - toc:
      permalink: true
      slugify: !!python/name:pymdownx.slugs.uslugify
  - pymdownx.arithmatex:
      generic: true
  - pymdownx.betterem:
      smart_enable: all
  - pymdownx.caret
  - pymdownx.details
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.keys
  - pymdownx.mark
  - pymdownx.smartsymbols
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.tasklist:
      custom_checkbox: true
  - pymdownx.tilde

# 插件
plugins:
  - search:
      lang:
        - zh
        - en
  - git-revision-date-localized:
      enable_creation_date: true
      type: datetime

# 导航结构
nav:
  - 首页: index.md
  - 快速开始: quick-start.md
  - 配置说明:
      - 环境变量: configuration.md
      - 信息源配置: sources.md
  - 飞书集成: feishu-sync.md
  - 早报模板: template.md
  - 产品需求: prd.md
  - 更新日志: changelog.md

# 额外配置
extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/ryanmind/ai-brief-starter
  analytics:
    feedback:
      title: 这篇文档有帮助吗？
      ratings:
        - icon: material/thumb-up
          name: 有帮助
          data: 1
          note: 感谢反馈！
        - icon: material/thumb-down
          name: 没帮助
          data: 0
          note: 感谢反馈，我们会持续改进。

extra_css:
  - stylesheets/extra.css

extra_javascript:
  - javascripts/extra.js
```

### 2.3 创建文档目录结构

```bash
# 创建 docs 目录（如果不存在）
mkdir -p docs/stylesheets
mkdir -p docs/javascripts
```

最终目录结构：

```
ai-brief-starter/
├── mkdocs.yml           # MkDocs 配置
├── docs/
│   ├── index.md         # 首页
│   ├── quick-start.md   # 快速开始
│   ├── configuration.md # 配置说明
│   ├── sources.md       # 信息源配置
│   ├── feishu-sync.md   # 飞书同步（已有）
│   ├── template.md      # 模板说明
│   ├── prd.md           # 产品需求
│   ├── changelog.md     # 更新日志
│   ├── stylesheets/
│   │   └── extra.css    # 自定义样式
│   └── javascripts/
│       └── extra.js     # 自定义脚本
└── ...
```

---

## 三、创建文档内容

### 3.1 首页 (docs/index.md)

```markdown
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
```

### 3.2 快速开始 (docs/quick-start.md)

从现有 README.md 提取核心内容。

### 3.3 配置说明 (docs/configuration.md)

```markdown
# 环境变量配置

## 必需配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `QWEN_API_KEY` | 阿里百炼 API Key | `sk-xxxxxx` |

## 可选配置

### 模型配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `QWEN_MODEL` | `qwen-flash` | Qwen 模型名称 |
| `MAX_ITEMS` | `120` | 最大抓取条数 |
| `TOP_N` | `20` | 最终输出条数 |

### 内容控制

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `BRIEF_MAX_CHARS` | `160` | 摘要最大字符数 |
| `DETAIL_MAX_CHARS` | `260` | 详情最大字符数 |
| `IMPACT_MAX_CHARS` | `140` | 影响分析最大字符数 |

### 过滤配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `STRICT_PRIMARY_ONLY` | `1` | 开启一手来源过滤 |
| `STRICT_AI_TOPIC_ONLY` | `1` | 开启 AI 主题过滤 |
| `HISTORY_DEDUP_DAYS` | `2` | 跨天去重天数 |

### 飞书配置

| 变量名 | 说明 |
|--------|------|
| `FEISHU_WEBHOOK_URL` | 飞书群机器人 Webhook |
| `FEISHU_APP_ID` | 飞书应用 ID |
| `FEISHU_APP_SECRET` | 飞书应用密钥 |
```

### 3.4 自定义样式 (docs/stylesheets/extra.css)

```css
/* 自定义样式 */
.md-content {
  max-width: 900px;
}

/* 中文排版优化 */
.md-content p {
  line-height: 1.8;
}

/* 代码块优化 */
.md-content pre {
  border-radius: 8px;
}

/* 表格优化 */
.md-content table {
  font-size: 0.9em;
}
```

---

## 四、本地预览

```bash
# 启动本地服务器
mkdocs serve

# 访问 http://127.0.0.1:8000 预览
```

修改文档后会自动热更新。

---

## 五、GitHub Actions 自动部署

### 5.1 创建工作流文件

创建 `.github/workflows/docs.yml`：

```yaml
name: docs

on:
  push:
    branches:
      - master
    paths:
      - 'docs/**'
      - 'mkdocs.yml'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: docs-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 获取完整历史，用于 git-revision-date 插件

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install mkdocs mkdocs-material

      - name: Build documentation
        run: mkdocs build --strict

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

### 5.2 启用 GitHub Pages

1. 进入仓库 **Settings** → **Pages**
2. **Source** 选择 **GitHub Actions**
3. 推送代码后自动触发部署

---

## 六、自定义域名（可选）

### 6.1 配置 CNAME

在 `docs/` 目录下创建 `CNAME` 文件：

```
docs.yourdomain.com
```

### 6.2 DNS 配置

在你的域名服务商添加 CNAME 记录：

| 类型 | 名称 | 值 |
|------|------|-----|
| CNAME | docs | your-username.github.io |

### 6.3 更新 mkdocs.yml

```yaml
site_url: https://docs.yourdomain.com/
```

---

## 七、常用命令速查

| 命令 | 说明 |
|------|------|
| `mkdocs serve` | 本地预览（热更新） |
| `mkdocs build` | 构建静态站点 |
| `mkdocs build --strict` | 严格模式构建（警告视为错误） |
| `mkdocs gh-deploy` | 手动部署到 GitHub Pages |

---

## 八、常见问题

### Q: 部署失败，提示 `mkdocs: command not found`

确保 `requirements.txt` 中包含：
```
mkdocs>=1.5.0
mkdocs-material>=9.4.0
```

### Q: 中文搜索不工作

确保 `mkdocs.yml` 中 search 插件配置了 `lang: zh`。

### Q: 如何添加 Google Analytics？

在 `mkdocs.yml` 添加：
```yaml
extra:
  analytics:
    provider: google
    property: G-XXXXXXXXXX
```

### Q: 如何添加评论系统？

可以使用 Giscus（基于 GitHub Discussions）或 Disqus。Material 主题官方有详细集成指南。

---

## 九、进阶配置

### 9.1 添加版本切换

```yaml
extra:
  version:
    provider: mike
```

配合 mike 插件实现多版本文档。

### 9.2 添加标签系统

```yaml
plugins:
  - tags
```

### 9.3 添加博客功能

使用 mkdocs-blogging-plugin 插件。

---

## 十、参考资源

- [MkDocs 官方文档](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [GitHub Pages 文档](https://docs.github.com/en/pages)
- [MkDocs 插件目录](https://github.com/mkdocs/mkdocs/wiki/MkDocs-Plugins)
