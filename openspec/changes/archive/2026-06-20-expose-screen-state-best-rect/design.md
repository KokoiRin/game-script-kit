## Context

OpenCV 模板匹配会返回最佳分数和最佳位置。当前 adapter 已保留最佳分数，但未达阈值时丢弃了最佳位置。状态识别调试需要知道“最像的位置”在哪里，以辅助判断截图区域和素材是否正确。

## Decisions

- 在 `ImageBatchMatchResult` 上新增可选 `best_rect`。
- 在 `ScreenStateCandidateResult` 上新增可选 `best_rect`。
- 命中时 `best_rect` 与 `match.rect` 相同。
- 未命中但模板尺寸合法且匹配执行成功时，`best_rect` 保留 OpenCV 最佳位置换算后的屏幕坐标。
- 模板大于搜索图、候选被跳过或无法执行匹配时，`best_rect` 为 `None`。
- `star probe-state --json` 将 `best_rect` 输出为 `{left, top, width, height}` 或 `null`。
- CLI 文本和 UI 文本以紧凑格式展示最佳位置，例如 `x=10,y=20,w=30,h=40`。

## Non-Goals

- 不新增图片叠框预览。
- 不自动更新配置区域。
- 不把 `best_rect` 用于状态选择或点击行为。
