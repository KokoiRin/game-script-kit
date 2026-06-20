## Why

区域诊断图能看到识别区域框是否大致正确，但用户要重截或核对模板时，还需要直接看到每个命名区域内实际截到了什么。把命名区域裁剪成独立图片，可以让状态识别素材调试更直接，也更适合命令行和 harness 使用。

## What Changes

- 新增 application 用例：保存当前屏幕中每个状态识别命名区域的裁剪图。
- 新增 `star capture-region-crops` 子命令。
- 输出每个裁剪图保存路径，方便用户打开或作为模板重截依据。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `screen-state-probe`: CLI 截图诊断增加命名区域裁剪导出。

## Impact

- 影响 application 截图诊断用例和 CLI 入口。
- 需要补充 application 与 CLI 行为测试。
- 不修改状态识别匹配规则、配置格式或 UI 行为。
