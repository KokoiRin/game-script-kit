## Context

现有脚本运行链路：

```text
LocalControlApplication.start_named_script
  -> run_script
  -> ScriptRunner
  -> InputDevice / condition ports
```

`RunLogger` 已经能承载图片匹配耗时等文本日志，但它不是结构化事件模型。后台 UI 会话保存 stdout/stderr 文本和 exit code，却没有结束原因字段。

## Goals / Non-Goals

**Goals:**
- 让 application 层状态明确表达脚本为什么结束。
- 让 runner 在步骤边界输出可读、可测试的事件日志。
- 保持现有 stdout/stderr 兼容，避免前端必须一次性重写。

**Non-Goals:**
- 不实现完整回放、截图留档或数据库存储。
- 不新增 DSL 语义。
- 不重做网页 UI，本轮只规划后续展示方式。

## Decisions

- `ScriptRunResult` 持有 `finish_reason`，由 `run_script` 统一映射异常类型。
- `ScriptRunStatus` 持有 `finish_reason` 和 `events`，后台会话结束时保存最终原因。
- 通过可选的 `emit_step_events` 开关启用步骤事件，避免影响同步 dry-run 的旧输出。
- `RunLogger` 仍保留 `log(message)`；支持事件的 logger 可以额外实现 `log_event(event)`，不强制所有 logger 修改。
- 事件同时写入结构化列表和文本 stdout，当前 UI 可立刻看到步骤日志。

## Risks / Trade-offs

- 文本日志会变多，长脚本可能产生大量事件；第一版先复用现有日志区，后续 UI 再做折叠和筛选。
- `WaitUntil` 高频轮询会产生日志；后续可以按事件类型或成功/失败过滤展示。

## UI Log Display Plan

第一阶段保持现有日志区，把 `stdout/stderr` 作为完整文本流展示，并在状态栏显示 `finish_reason` 的中文含义。

第二阶段基于 `events` payload 增加结构化事件列表：
- 顶部显示运行摘要：运行中/结束原因、退出码、事件总数、最后失败步骤。
- 主体按步骤路径分组展示事件，成功步骤折叠，失败步骤默认展开。
- 图片匹配和 WaitUntil 轮询作为可筛选的诊断事件，默认只展示最近 N 条或失败相关条目。
- stderr 单独作为错误面板固定在底部，避免和普通步骤日志混在一起。

第三阶段再考虑运行历史、截图关联和事件导出；这些不进入本轮实现。
