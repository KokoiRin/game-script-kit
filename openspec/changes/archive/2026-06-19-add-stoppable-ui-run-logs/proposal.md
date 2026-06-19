## Why

长时间轮询脚本在本地 UI 中运行时，目前请求会一直占用，用户无法从页面停止；同时图片匹配耗时不可见，难以判断慢在截图、匹配还是脚本等待。现在已经开始使用“离开/重来”这类持续脚本，需要把运行控制和诊断日志补上。

## What Changes

- 本地 UI 运行脚本改为后台运行会话，页面提供停止按钮并可轮询当前运行状态。
- 脚本执行引擎支持可注入取消检查，长循环或等待过程中能尽快停止并返回取消结果。
- 图片匹配查询记录每次模板匹配耗时、模板路径、是否命中和置信度，并在 UI 日志中展示。
- 保持 CLI 同步运行路径不变；新的停止能力首先服务本地 UI。

## Capabilities

### New Capabilities

### Modified Capabilities
- `local-control-ui`: UI 可以启动、查询并停止后台脚本运行，并展示运行日志。
- `game-script-core`: `ScriptRunner` 支持可注入取消检查，取消时停止后续步骤。
- `screen-image-matching`: 图片查询路径可报告匹配耗时和结果摘要，供上层诊断。

## Impact

- 影响 `portable.engine.runner`、图片查询路径和 application 层本地控制用例。
- 影响本地 UI HTTP API 和页面按钮状态。
- 新增测试覆盖后台运行状态、停止请求和图片匹配耗时日志。
