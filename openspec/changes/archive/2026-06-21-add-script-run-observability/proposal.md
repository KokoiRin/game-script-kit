## Why

真实游戏脚本运行时，用户需要知道每个行为是否执行、条件为什么走某条分支，以及脚本结束是正常完成、取消、超时还是失败。当前 UI 只有 stdout/stderr 和 exit code，图片匹配日志也是纯文本，无法稳定表达“结束原因”和“步骤事件”。

## What Changes

- 为脚本运行结果增加结构化结束原因，区分 completed、cancelled、timed_out、failed、setup_failed、configuration_failed 等情况。
- 在 runner 执行步骤时产生步骤事件日志，覆盖步骤开始/成功/失败、点击解析、等待、Repeat 轮次、If 分支和 WaitUntil 轮询。
- 后台脚本状态 HTTP payload 暴露结束原因和结构化事件，同时继续保留 stdout/stderr 文本日志。
- 本轮不修改脚本 DSL，不修改 CLI 子命令名，不改变现有命令入口。

## Capabilities

### Modified Capabilities

- `game-script-core`: runner 在不改变脚本执行语义的前提下输出步骤事件。
- `local-control-ui`: 后台脚本状态暴露结构化结束原因和运行事件。

## Impact

- 影响 engine runner、application script run/local control、local UI HTTP payload 和相关测试。
- 前端第一步可继续展示文本日志；后续可基于事件 payload 设计更清晰的日志面板。
