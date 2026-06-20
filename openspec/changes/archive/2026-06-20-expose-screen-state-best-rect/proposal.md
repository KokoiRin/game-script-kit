## Why

状态识别现在能显示 `best_confidence`，但当候选未命中时，用户仍然不知道底层匹配认为“最像”的位置在哪里。调素材和区域时，这个位置比单独分数更有用：如果最佳位置落在区域外或明显不相关，说明区域或素材需要重截；如果位置接近目标但分数偏低，说明可能是阈值或素材质量问题。

## What Changes

- 批量图片匹配结果保留 `best_rect`，表示本次模板匹配得到的最佳位置。
- 界面状态候选结果携带 `best_rect`。
- `star probe-state --json` 输出每个候选的 `best_rect`。
- 本地 UI 的界面探测候选列表展示最佳位置。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `screen-state-probe`: 状态探测候选结果暴露最佳匹配位置，用于素材和区域校准。
- `local-control-ui`: UI 候选列表展示最佳匹配位置。

## Impact

- 影响领域结果模型、桌面图像匹配 adapter、状态探测转换、CLI 输出、UI application summary、HTTP payload 和前端渲染。
- 不改变状态命中阈值、状态选择规则、早停规则、脚本条件语义或 `assets/screen-states.json` 格式。
