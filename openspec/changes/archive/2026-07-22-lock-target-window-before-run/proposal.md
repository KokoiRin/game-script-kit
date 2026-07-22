## Why

Star 已能在运行前激活目标应用，但一个应用可能同时有多个顶层窗口，且当前图片搜索仍默认覆盖整块屏幕。即使 Safari 被激活，Star 仍可能在错误窗口或其他应用的相似图片上命中。项目需要按窗口标题选择具体窗口，并把脚本坐标和默认识图范围绑定到该窗口。

## What Changes

- 为 `star run` 和 `star run-plan` 增加 `--target-window-title` 参数，要求同时指定 `--target-app`。
- 真实运行先激活应用，再通过应用层 port 查找并 Raise 标题匹配的顶层窗口。
- 将目标窗口屏幕矩形绑定为本轮脚本的 `AreaWindow`，使点位按窗口左上角解析。
- 补齐 `Window` 的图片搜索区域语义：`AreaWindow` 无显式区域时默认限制在整个窗口，有显式区域时按窗口原点偏移。
- 新增 macOS AppKit + Accessibility adapter，通过窗口标题、位置和尺寸完成选择与 Raise。
- 目标窗口缺失、标题歧义或权限错误时作为 setup failure 停止，不执行鼠标动作。
- 更新视觉靶场 smoke，验证错误前台和多个 Safari 顶层窗口下仍能命中靶场窗口。

## Capabilities

### New Capabilities

- `target-window-locking`: 定义运行前选窗、窗口范围绑定、macOS 接入和错误行为。

### Modified Capabilities

- `script-action-model`: 补充 `Window` 对默认及显式图片搜索区域的解析语义。

## Impact

- 修改窗口领域协议、条件/图片目标区域解析、脚本运行 application、macOS adapter、composition 和 CLI。
- 不修改脚本 JSON 格式、图片匹配算法、鼠标 adapter 或状态探测配置。
- 不新增第三方依赖；复用当前 macOS 环境已有的 PyObjC AppKit 与 Accessibility 框架。
