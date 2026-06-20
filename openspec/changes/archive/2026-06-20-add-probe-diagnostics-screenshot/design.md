## Context

已有 `capture-region-diagnostics` 会保存一张带命名区域框的截图，已有 `probe-state --json` 会输出每个候选的 `best_rect`。新能力复用这两条链路：application 层先执行一次状态探测，再保存当前屏幕截图，并把区域和候选最佳位置都绘制到输出图上。

## Decisions

- 输出路径为 `.star/debug/screenshots/latest-screen-probe.png`。
- CLI 子命令命名为 `capture-probe-diagnostics`，支持 `--min-confidence`，默认 `0.8`。
- UI 新增按钮复用现有诊断预览区域，不新增单独图片资源 endpoint。
- 如果 `assets/screen-states.json` 存在且包含命名区域，诊断图绘制区域框；没有命名区域时仍可只绘制候选 `best_rect`。
- 如果探测失败、截图能力缺失或屏幕尺寸不可用，返回非零 `ControlResult` 并展示清晰错误。
- 候选被跳过或没有 `best_rect` 时不绘制候选框。

## Non-Goals

- 不复用同一张截图执行探测和绘图；第一版允许探测截图与诊断截图之间存在轻微时间差。
- 不自动调整 `screen-states.json` 的区域。
- 不新增图片编辑或素材重截功能。
