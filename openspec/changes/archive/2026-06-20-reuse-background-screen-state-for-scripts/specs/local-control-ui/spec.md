## ADDED Requirements

### Requirement: 脚本复用运行中的后台界面探测状态
本地控制 application SHALL 在真实脚本读取当前界面状态时优先复用正在运行的后台界面探测状态。只有后台探测正在运行且当前状态不是 `未知` 时，系统 MAY 复用该状态；否则 MUST 执行现有即时状态探测。

#### Scenario: 运行中的后台探测提供状态
- **GIVEN** 后台界面探测正在运行
- **AND** 最近探测状态为 `主页`
- **WHEN** 真实脚本评估 `ScreenStateIs("主页")`
- **THEN** 脚本状态 reader 返回 `主页`
- **AND** 系统不为该次状态读取额外执行即时探测
- **AND** 脚本运行日志说明状态来自后台界面探测

#### Scenario: 没有可用后台状态
- **GIVEN** 后台界面探测未运行或最近状态为 `未知`
- **WHEN** 真实脚本评估 `ScreenStateIs("主页")`
- **THEN** 系统执行即时状态探测获取当前状态
