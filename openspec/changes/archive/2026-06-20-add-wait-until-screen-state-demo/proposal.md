## Why

项目已经支持 `ScreenStateIs` 条件和 `WaitUntil` 条件等待，但默认脚本里只有状态分支示例。游戏脚本更常见的写法是“等到某个界面出现后再继续”，需要一个可直接在 CLI/UI 里查看和 dry-run 的内置示例。

## What Changes

- 新增默认命名脚本 `wait-until-screen-state-demo`。
- 脚本等待当前界面状态变为 `主页`，随后执行一个示例点击。
- 脚本详情和 dry-run 可以展示状态等待写法，帮助用户理解状态识别如何进入脚本流程。

## Capabilities

### New Capabilities

### Modified Capabilities

- `script-management`: 默认脚本 catalog 增加界面状态等待示例脚本。

## Impact

- 影响内置脚本注册、脚本 catalog 测试和 CLI/UI 脚本详情展示。
- 不改变 `WaitUntil`、`ScreenStateIs`、状态探测或 runner 执行语义。
