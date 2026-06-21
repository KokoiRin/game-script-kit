## Decision

引擎层引入一个内部正常停止信号，用于表达“脚本前置条件未满足，后续动作不应继续执行”。application 层把该信号归一化为 `exit_code=0`、`finish_reason=completed`，并通过结构化事件向 UI 说明停止原因。

## Scope

- `WaitUntil` 超时属于未满足前置条件，正常停止。
- `Click(ImageTarget(...))` 定位返回 `None` 属于目标未出现，正常停止。
- 资源解析失败、端口缺失和 adapter 运行异常仍然抛错。

## UI Logging

UI 只展示关键运行日志：

- 脚本开始和结束。
- 等待条件满足或超时停止。
- 图片目标定位成功或未找到停止。
- 实际点击、等待动作和错误。

`WaitUntil` 每轮 `condition_evaluated` 不直接展示，避免长时间轮询刷屏。后续如果需要诊断级日志，可以单独加“详细日志”开关。
