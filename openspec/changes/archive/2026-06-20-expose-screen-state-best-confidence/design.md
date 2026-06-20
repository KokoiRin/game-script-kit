## Context

OpenCV 模板匹配总能返回一个最佳分数，但当前 adapter 在分数低于阈值时只返回 `match=None`，调用方无法看到分数。状态识别调试需要这个分数来判断素材和区域质量。

## Decisions

- 在 `ImageBatchMatchResult` 上新增可选 `best_confidence`。
- 在 `ScreenStateCandidateResult` 上新增可选 `best_confidence`。
- 命中时 `best_confidence` 与 `confidence` 相同。
- 未命中但模板尺寸合法且匹配执行成功时，`best_confidence` 保留 OpenCV 最佳分数。
- 模板大于搜索图等无法执行匹配的情况，`best_confidence` 为 `None`。
- 状态选择仍只看 `match` 是否存在，不使用 `best_confidence`。

## Non-Goals

- 不改变默认阈值。
- 不改变 `probe_screen_state(..., stop_on_first_match=True)` 的早停策略。
- 不新增自动调阈值或自动重截模板能力。
