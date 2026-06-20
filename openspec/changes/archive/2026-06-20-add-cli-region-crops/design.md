## Context

`capture_screen_region_diagnostics()` 已经会读取 `assets/screen-states.json` 的命名区域，保存当前屏幕截图，并使用 `_region_box_in_pixels(...)` 把点坐标区域换算为截图像素区域。区域裁剪应复用同一套配置解析、截图获取和坐标换算逻辑，避免诊断框与裁剪图不一致。

## Decisions

- 新增 `LocalControlApplication.capture_screen_region_crops()`。
- 该用例保存一张最新原始截图，并按每个命名区域输出独立 PNG。
- 裁剪图目录为 `.star/debug/screenshots/regions/`。
- 裁剪图文件名使用区域名并做最小安全清理，避免路径分隔符进入文件名。
- CLI 新增 `star capture-region-crops`，只负责调用 application 并打印 `ControlResult`。

## Non-Goals

- 不新增 UI 按钮。
- 不自动更新 `assets/screen-states.json`。
- 不自动生成或覆盖模板素材。
