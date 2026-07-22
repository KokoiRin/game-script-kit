## Context

上一轮 `--target-app` 只保证应用进入前台。当前 `ScreenImageLocator` 在未传 `region` 时截取整屏，而 `AreaWindow` 只有点坐标偏移能力：图片条件或图片目标未声明区域时仍会搜索整屏。要让“目标窗口”成为可靠边界，需要同时解决平台选窗和 portable Window 搜索范围两个问题。

## Goals / Non-Goals

**Goals:**

- 根据目标应用和窗口标题子串选择唯一的可见顶层窗口。
- 在 runner 创建前 Raise 目标窗口并取得它的屏幕矩形。
- 本轮脚本使用目标窗口左上角作为点坐标原点。
- 无显式区域的图片条件和图片目标默认只搜索目标窗口。
- 失败在应用层归一化为 setup failure，输入 device 不被创建。
- Run Plan 每个脚本项重新解析窗口，适应窗口移动。

**Non-Goals:**

- 不枚举或选择同一浏览器窗口内部的标签页。
- 不移动、缩放、恢复最小化窗口。
- 不持续监控运行期间窗口是否移动或被遮挡。
- 不让 `ScreenStateIs` 在本轮自动继承脚本窗口；状态探测仍使用自身配置区域。
- 不把平台窗口标题写入脚本 JSON。

## Decisions

### 使用运行参数而不是脚本模型保存平台标题

新增 `--target-window-title`，并要求同时提供 `--target-app`。窗口标题和应用名是本机运行环境信息，不进入跨平台脚本 DSL。Run Plan 将同一参数传给每个脚本项。

### 应用层把选窗结果转换为 AreaWindow

新增 `ApplicationWindowController` port，返回窗口标题和 `Rect`。`run_script` 在真实运行前按“激活应用 → 选择并 Raise 窗口 → 用 `AreaWindow` 替换本轮 Script 窗口 → 创建 runner”的顺序准备环境。

使用 `dataclasses.replace` 生成本轮脚本副本，不修改 catalog 中的原脚本。未指定窗口标题时保持上一轮行为。

### Window 统一解析图片搜索区域

为 `Window` 增加 `resolve_region(region)`：

- `ScreenWindow`：保留显式屏幕区域；无区域时返回 `None`，表示整屏。
- `AreaWindow`：显式区域按窗口左上角偏移；无区域时返回窗口自身矩形。

条件评估和图片目标统一调用该方法，避免两处重复窗口规则。

### macOS 使用 AppKit 进程解析与 Accessibility 窗口树

adapter 使用 AppKit 按本地化名、bundle id 或可执行文件名解析目标应用 pid，再从该进程的 Accessibility tree 读取顶层窗口标题、位置和尺寸。标题匹配必须唯一；随后对匹配窗口执行 `AXRaise`。

平台 API、权限和返回值转换全部封装在 adapter backend 内，单元测试使用 fake backend，不把 PyObjC 类型带进 application 或 domain。

## Risks / Trade-offs

- [浏览器标签页不是独立顶层窗口] → 第一版只选 OS 顶层窗口；真实 smoke 为靶场使用单独 Safari 窗口。
- [两个窗口标题同时包含相同文本] → 拒绝歧义并要求更具体的标题，不猜测。
- [窗口移动后旧矩形失效] → 每个脚本开始前重新解析；脚本运行中移动窗口不处理。
- [Accessibility 权限不足] → 返回 setup failure，提示检查辅助功能权限，不执行鼠标。
- [窗口部分被其他应用遮挡] → Raise 后再等待短暂稳定；不实现持续置顶。

## Migration Plan

不传 `--target-window-title` 时行为不变。现有显式图片区域在 `ScreenWindow` 下不变；`AreaWindow` 无显式区域的图片搜索会从整屏收紧到自身矩形，这是预期的边界修正。

## Open Questions

无。第一版先验证顶层窗口锁定能否消除当前多窗口误命中问题。
