## Why

项目已经支持 `WaitUntil(ScreenStateIs(...))`，但脚本详情目前只把它显示为普通步骤。用户在 UI 中查看脚本时会看到“状态决策：没有状态决策”，却看不到“这个脚本正在等待哪个界面状态”，不利于理解状态识别如何驱动脚本流程。

## What Changes

- 脚本详情结果新增结构化的状态等待摘要，用于列出 `WaitUntil(ScreenStateIs(...))` 引用的状态。
- CLI `star details <name>` 输出新增“状态等待”分组。
- 本地 UI 脚本详情新增“状态等待”分组，并根据当前探测状态展示等待是否已经满足。
- 不新增 DSL 语义，不改变 runner、状态探测或 dry-run 执行行为。

## Capabilities

### New Capabilities

### Modified Capabilities

- `script-management`: 脚本详情需要展示状态等待摘要，帮助用户理解状态等待脚本。

## Impact

- 影响 application 层脚本详情 presenter、CLI details 输出、本地 UI JSON payload 和静态页面展示。
- 需要补充脚本详情、CLI 和 UI adapter 的行为测试。
