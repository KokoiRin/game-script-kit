## Why

脚本详情已经能展示脚本依赖的界面状态，但用户调试状态条件脚本时仍要手动把状态名填到 dry-run 输入里。把状态依赖作为可操作信息暴露给 UI，可以让脚本调试更自然，也为后续脚本依赖检查和状态驱动执行铺路。

## What Changes

- 脚本详情结果新增结构化的界面状态依赖列表，独立于可读依赖文案。
- 本地 UI 的脚本详情接口返回该结构化状态依赖列表。
- 本地 UI 提供“使用脚本状态”操作，把当前选中脚本的第一个状态依赖填入 dry-run 模拟状态输入。
- 无状态依赖时，该操作不得改写用户当前输入，并展示清晰提示。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `local-control-ui`: 脚本详情接口和页面增加可操作的状态依赖，用于填充 dry-run 模拟状态。

## Impact

- 影响 `portable.application.script_details` 的脚本详情结果模型。
- 影响本地 UI HTTP payload 和前端交互。
- 需要补充 application、HTTP adapter 和静态 UI 行为测试。
