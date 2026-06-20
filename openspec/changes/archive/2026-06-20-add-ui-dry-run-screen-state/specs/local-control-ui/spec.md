## ADDED Requirements

### Requirement: UI dry-run 支持指定当前界面状态
本地控制 UI SHALL 允许用户在运行命名脚本时指定 dry-run 当前界面状态。HTTP adapter MUST 把该值传给 application 层脚本运行用例；application 层 MUST 用该值作为 `ScreenStateIs` 条件的 dry-run 状态来源。

#### Scenario: 页面展示模拟状态输入
- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示用于 dry-run 的模拟界面状态输入
- **AND** 该输入默认值为 `未知`

#### Scenario: dry-run 状态条件脚本使用模拟状态
- **WHEN** 用户在 UI 中输入模拟状态 `主页`
- **AND** 用户以 dry-run 模式运行包含 `ScreenStateIs("主页")` 的脚本
- **THEN** 系统通过 application 层使用 `主页` 作为 dry-run 当前状态
- **AND** 脚本按状态条件命中路径执行
