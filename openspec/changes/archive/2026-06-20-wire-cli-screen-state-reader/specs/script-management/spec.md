## ADDED Requirements

### Requirement: CLI 真实运行注入界面状态读取 adapter

系统 SHALL 在真实运行包含 `ScreenStateIs` 条件的命名脚本时注入本地桌面界面状态读取 adapter，使 runner 可以通过 `ScreenStateReader` 端口参考当前识别到的界面状态。CLI MUST 复用 application 层状态探测 reader，不得在入口层执行图片匹配或解释状态识别规则。

#### Scenario: macOS 模式运行界面状态条件脚本

- **WHEN** 用户通过 `star run <name>` 真实运行包含 `ScreenStateIs("主页")` 的命名脚本
- **THEN** 系统会同时加载输入设备 adapter 和界面状态读取 adapter，并把它们注入 ScriptRunner

#### Scenario: dry-run 状态条件脚本仍使用固定状态

- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-screen-state 主页` 运行包含 `ScreenStateIs("主页")` 的命名脚本
- **THEN** 系统继续使用 dry-run 固定状态评估条件
- **AND** 不读取真实屏幕状态
