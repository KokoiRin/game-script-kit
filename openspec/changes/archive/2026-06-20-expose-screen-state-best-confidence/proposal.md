## Why

`probe-state` 目前对未命中候选只显示 `confidence=null`。用户调素材和区域时无法判断“只差一点低于阈值”还是“区域/素材完全不对”。保留每个候选的最佳匹配置信度，可以让状态识别调试更直接。

## What Changes

- 批量图片匹配结果保留 `best_confidence`，即使没有达到最低阈值。
- 界面状态候选结果携带 `best_confidence`。
- `star probe-state --json` 输出每个候选的 `best_confidence`。
- 文本输出增加最佳置信度展示。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `screen-state-probe`: 状态探测候选结果暴露未命中时的最佳匹配置信度。

## Impact

- 影响领域结果模型、桌面批量图像匹配 adapter、状态探测转换和 CLI 输出。
- 不改变状态命中阈值、早停规则或脚本条件语义。
