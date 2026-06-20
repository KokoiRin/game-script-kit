## Context

`LocalControlApplication` 已经有 `capture_screen_screenshot()` 和 `capture_screen_region_diagnostics()`。UI 已通过 HTTP 调用这些 use case。CLI 只需要增加薄入口，调用 application 并打印 `ControlResult`。

## Decisions

- `star capture-screen` 调用 `build_local_control_application().capture_screen_screenshot()`。
- `star capture-region-diagnostics` 调用 `build_local_control_application().capture_screen_region_diagnostics()`。
- stdout/stderr 和 exit code 直接使用 application 返回的 `ControlResult`。
- CLI 不解析 `assets/screen-states.json`，不绘制区域，不直接访问截图 adapter。

## Non-Goals

- 不新增自定义输出路径参数。
- 不新增素材裁剪或模板生成能力。
- 不修改 UI 诊断按钮。
