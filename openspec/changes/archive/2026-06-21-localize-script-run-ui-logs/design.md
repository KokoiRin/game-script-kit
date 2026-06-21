## Context

脚本运行状态 payload 已包含：

- `stdout` / `stderr`：兼容文本日志。
- `events`：结构化步骤事件。
- `finish_reason`：结构化结束原因。

当前 UI 黑色框直接展示 stdout/stderr，因此事件文本仍是 `script event type=...` 形式。

## Decisions

- 前端渲染优先使用 `events` 生成中文行，保留结构化事件字段不变。
- stdout 中以 `script event ` 开头的兼容行不展示，避免和 events 重复。
- stdout/stderr 其他常见英文行在前端按已知格式翻译，无法识别的行原样保留。
- 日志刷新后自动滚动到底部，适合持续运行脚本。

## Non-Goals

- 不做折叠、筛选、历史记录或事件导出。
- 不修改后端事件字段名。
