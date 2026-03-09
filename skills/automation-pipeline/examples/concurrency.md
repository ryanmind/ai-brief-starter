# Concurrency Examples

`concurrency` 控制着同一组 Workflow 或 Job 的并发行为。它能够防止多个 workflow runs 同时修改共享状态。

## 1. 自动取消旧的构建 (Cancel in Progress)

这是在 Pull Request (PR) 中最常用的模式。当开发者连续 push 新的代码到同一个 PR 时，取消之前还在排队或运行中的旧构建，以节省 Runner 资源。

```yaml
concurrency:
  # 将 group 按 workflow 名称加 PR number 或分支名分组
  group: ${{ github.workflow }}-${{ github.ref }}
  # 取消进行中的同一 group run
  cancel-in-progress: true
```

## 2. 串行部署 (Queueing / Serial Deployment)

在向生产环境或 Staging 环境部署时，绝不能同时执行两次部署任务，否则会导致资源竞争或状态冲突。此时**不要**开启 `cancel-in-progress`。

```yaml
concurrency:
  # 将 group 固定为环境名，确保同一环境下只存在一个部署进程
  group: production-deploy
  # 不要使用 cancel-in-progress，这样后触发的 run 会进入排队状态 (Pending)
  cancel-in-progress: false
```
