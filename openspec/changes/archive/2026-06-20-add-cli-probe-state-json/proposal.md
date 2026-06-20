## Why

`star probe-state` 目前只输出面向人阅读的中文文本。后续 harness、UI 前端或自然语言脚本编译器需要稳定读取当前状态和候选详情时，不应该解析展示文案。

## What Changes

- 为 `star probe-state` 增加 `--json` 参数。
- JSON 输出包含当前状态、是否识别到已知状态、总耗时和候选项详情。
- 保持默认文本输出、错误码和 stderr 行为不变。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `screen-state-probe`: CLI 单次界面状态探测增加机器可读 JSON 输出。

## Impact

- 影响 CLI 入口参数和输出格式。
- 需要补充 CLI 行为测试。
- 不修改状态识别规则、图片匹配 adapter 或脚本 DSL。
