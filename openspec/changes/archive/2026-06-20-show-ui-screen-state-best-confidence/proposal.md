## Why

`star probe-state --json` 已经可以输出候选的 `best_confidence`，但本地 UI 的界面探测 tab 仍只展示命中置信度。用户在 UI 中调状态识别时，如果候选未命中，仍然看不到“最佳相似度”，需要切回 CLI 才能判断素材或区域是否接近。

## What Changes

- 后台界面探测候选摘要携带 `best_confidence`。
- `/api/screen-state-probe` 的候选 JSON 输出 `best_confidence`。
- 本地 UI 候选列表展示最佳置信度。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `local-control-ui`: 界面探测候选展示最佳匹配置信度，未命中时也能辅助诊断。

## Impact

- 影响 application 层状态探测摘要、HTTP UI adapter、前端候选渲染和相关测试。
- 不改变图片匹配阈值、早停规则、状态选择规则或 `assets/screen-states.json` 格式。
