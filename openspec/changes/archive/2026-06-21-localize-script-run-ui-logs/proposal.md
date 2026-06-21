## Why

脚本后台运行已经暴露结构化事件，但 UI 黑色日志框仍直接拼接 stdout/stderr，用户看到的运行事件、图片匹配和状态判断日志包含英文标识，不利于快速判断每一步是否成功。

## What Changes

- 本地 UI 的脚本运行日志框优先根据 `events` payload 渲染中文日志。
- 过滤掉后端兼容用的英文 `script event ...` 文本行，避免重复展示。
- 对常见文本日志如图片匹配、界面状态条件、点击和等待进行中文化展示。
- 每次刷新脚本状态后自动滚动到日志底部。

## Capabilities

### Modified Capabilities

- `local-control-ui`: 脚本运行日志在停止按钮下方的输出框中以中文展示运行过程。

## Impact

- 仅修改前端展示和测试；不改变脚本 DSL、HTTP endpoint 或运行语义。
