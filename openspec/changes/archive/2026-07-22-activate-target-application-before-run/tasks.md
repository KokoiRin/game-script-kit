## 1. 应用层语义

- [x] 1.1 为真实运行激活、dry-run 不激活和激活失败添加行为测试。
- [x] 1.2 新增 `ApplicationActivator` port，并在 runner 创建前完成环境准备。

## 2. macOS 接入与入口

- [x] 2.1 为 macOS 系统命令调用、稳定等待和失败映射添加 adapter 测试。
- [x] 2.2 实现 macOS 应用激活 adapter，并通过本地桌面 composition 注入。
- [x] 2.3 为 `run`、`run-plan` 添加 `--target-app`，覆盖参数传递和 dry-run 冲突。

## 3. 靶场验收

- [x] 3.1 更新视觉靶场真实 smoke，使其通过目标应用激活能力启动。
- [x] 3.2 从非 Safari 前台状态完成真实截图、识图、点击和真值验收。

## 4. 验证

- [x] 4.1 运行相关行为测试和全量 pytest。
- [x] 4.2 运行严格 OpenSpec 校验和 `git diff --check`。
- [x] 4.3 归档 change 并提交完整功能。
