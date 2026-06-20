## Context

领域层的 `ScreenStateCandidateResult` 已经包含 `best_confidence`，CLI 也已经输出该字段。UI 目前的数据链路是：

`ScreenStateCandidateResult` -> `ScreenStateProbeCandidateSummary` -> `/api/screen-state-probe` JSON -> `renderScreenStateCandidates`

中间的 application summary 和 HTTP payload 尚未携带 `best_confidence`，导致前端无法展示。

## Decisions

- 在 `ScreenStateProbeCandidateSummary` 上新增可选 `best_confidence`。
- `_probe_candidate_summary()` 从领域候选结果复制 `best_confidence`。
- `_probe_candidates_to_payload()` 输出 `best_confidence`。
- 前端候选列表在现有置信度后追加“最佳”字段，格式化规则与 `confidence` 保持一致。
- 跳过候选的 `best_confidence` 保持为 `null`，前端显示为 `无`。

## Non-Goals

- 不改变后台探测统计口径。
- 不新增阈值调节建议或自动素材校准。
- 不修改截图区域配置或素材文件。
