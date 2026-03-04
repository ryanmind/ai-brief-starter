# MkDocs + GitHub Pages 搭建与运维指南

本文档面向本仓库，内容以当前代码为准，重点解决“如何稳定发布”和“为什么没更新”。

## 1. 当前架构（先看这个）

本项目有两条工作流：

- `ai-morning-brief`：生成早报，产出 `reports/latest.md`，并自动同步到 `docs/latest.md`
- `docs`：检测 `docs/**` 与 `mkdocs.yml` 变更，构建并发布到 GitHub Pages

因此，GitHub Pages 展示的是 `docs/` 目录内容，不直接读取 `reports/`。

## 2. 本地预览文档

```bash
pip install -r requirements.txt
mkdocs serve
```

访问 `http://127.0.0.1:8000`。

## 3. 文档入口与导航

文档导航由 `mkdocs.yml` 的 `nav` 决定。当前关键入口：

- `index.md`：首页
- `latest.md`：今日早报（由工作流自动覆盖更新）
- `history.md`：历史归档索引
- `quick-start.md`：快速开始
- `configuration.md`：环境变量
- `sources.md`：信息源配置
- `feishu_docs_guide_zh.md`：飞书配置

> 建议：`docs/latest.md` 不要手工长期维护，它会被每日任务自动更新。

## 4. 自动部署触发条件

`docs` 工作流会在以下场景触发：

- 分支：`master` 或 `mkdocs`
- 文件变更包含：`docs/**` 或 `mkdocs.yml`
- 文件变更包含：`requirements.txt`（保证文档依赖变化也会重建）
- 或手动点击 `Run workflow`

工作流构建命令：

```bash
pip install -r requirements.txt
mkdocs build --strict
```

## 5. 与每日早报联动机制

`ai-morning-brief` 成功后会执行：

1. 将 `reports/latest.md` 渲染为更易读的 MkDocs 页面格式
2. 写入 `docs/latest.md`
3. 将 `reports/YYYY-MM-DD.md` 渲染并写入 `docs/history/YYYY-MM-DD.md`
4. 重建历史索引 `docs/history.md`
5. 若内容有变化，自动提交并 push 到当前分支
6. 通过 `push` 触发 `docs` 工作流重新部署站点

所以“早报已生成但站点没更新”的排查顺序是：

1. 看 `ai-morning-brief` 是否成功
2. 看日志里是否执行了 `Sync latest brief to docs` 与 `Commit docs latest brief`
3. 看 `docs` 工作流是否被触发并成功部署

## 6. 常见问题

### Q1: 手动跑了 docs workflow，但没有新早报

`docs` 只负责构建发布，不负责采集和生成内容。先跑 `ai-morning-brief`。

### Q2: 站点首页更新了，但“今日早报”还是旧内容

通常是每日流程没有提交 `docs/latest.md`：

- 可能 `reports/latest.md` 未生成
- 可能当次内容与上次完全一致（不会重复提交）
- 可能 push 权限不足（检查 workflow 的 `permissions: contents: write`）

### Q3: 为什么部署成功但页面 404

检查：

1. 仓库 `Settings -> Pages` 的 Source 是否为 `GitHub Actions`
2. 访问路径是否正确：`https://ryanmind.github.io/ai-brief-starter/`
3. 是否刚部署完成（等待 1-3 分钟 CDN 刷新）

## 7. 推荐维护流程

1. 改文档：编辑 `docs/*.md` 或 `mkdocs.yml`
2. 本地检查：`mkdocs build --strict`
3. 提交并推送到 `master` 或 `mkdocs`
4. 在 Actions 确认 `docs` 工作流为绿色

---

参考：

- [MkDocs 官方文档](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [GitHub Pages 文档](https://docs.github.com/en/pages)
