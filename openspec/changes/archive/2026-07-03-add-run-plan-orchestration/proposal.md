## Why

当前用户已经可以把单个文件脚本写成可等待状态、等待图片并点击目标的自动化步骤，但一轮日常任务仍需要手动逐个运行脚本。用户需要在一次操作里选择多个已有脚本，让系统按顺序执行并输出每个脚本的结果，避免把多个任务硬编码成一个巨大脚本。

## What Changes

- 新增 Run Plan 编排能力：调用方传入一组脚本名称，系统按顺序运行这些已有脚本。
- Run Plan 默认遇到第一个未完整执行的脚本后停止后续脚本，包括条件未满足、失败、配置错误、setup 失败、超时或取消。
- CLI 新增 `star run-plan <script>...`，支持复用 `run` 的 dry-run、dry-run 图片依赖和 dry-run 状态参数。
- CLI 支持 `--continue-on-error`，允许某个脚本失败后继续执行后续脚本并汇总结果。
- 输出一轮计划摘要，包含每个脚本的序号、名称、退出码和结束原因。

## Capabilities

### Modified Capabilities

- `script-management`: 用户可以在一次命令中编排并运行多个已有命名脚本。

## Impact

- 影响 application 层脚本编排、CLI 参数和输出、相关测试。
- 不新增脚本 DSL，不新增平台 adapter；单脚本正常停止仍保持成功退出码，但会暴露 `stopped_unmet_condition` 结束原因。
