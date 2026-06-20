## 1. Application 用例

- [x] 1.1 添加 application 层测试，覆盖诊断命令会先截图再探测并合并输出。
- [x] 1.2 添加 application 层测试，覆盖截图失败时不执行状态探测。
- [x] 1.3 在 `LocalControlApplication` 中实现屏幕识别环境诊断组合用例。

## 2. CLI 入口

- [x] 2.1 添加 CLI 测试，覆盖 `diagnose-screen` 输出和最低置信度参数传递。
- [x] 2.2 在 CLI 中注册 `diagnose-screen` 子命令并打印 application 结果。

## 3. 验证和归档

- [x] 3.1 运行相关 pytest 和 OpenSpec 校验。
- [x] 3.2 运行真实 `star diagnose-screen` smoke test。
- [x] 3.3 完成 OpenSpec 任务勾选并归档变更。
