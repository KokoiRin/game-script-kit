## ADDED Requirements

### Requirement: CLI 提供屏幕识别环境诊断入口

系统 SHALL 提供 `star diagnose-screen` 子命令，用于一次性执行屏幕截图诊断和单轮界面状态探测。CLI MUST 复用 application 层组合用例，不得在入口层直接截图、执行图片匹配或解释状态探测规则。

#### Scenario: 输出屏幕诊断摘要
- **WHEN** 用户运行 `star diagnose-screen`
- **THEN** 系统保存一张当前屏幕诊断截图
- **AND** 系统执行一轮界面状态探测
- **AND** stdout 输出截图保存路径、当前状态、总耗时和候选探测结果
- **AND** CLI 返回 application 层组合用例的退出码

#### Scenario: 保留截图警告和状态提示
- **WHEN** 用户运行 `star diagnose-screen`
- **AND** 截图诊断产生疑似全黑截图警告
- **AND** 状态探测结果包含诊断提示
- **THEN** stderr 输出截图警告
- **AND** stdout 输出状态探测提示
- **AND** 状态探测仍然执行

#### Scenario: 传递最低置信度
- **WHEN** 用户运行 `star diagnose-screen --min-confidence 0.75`
- **THEN** 系统使用 `0.75` 作为本次状态探测最低置信度

#### Scenario: 截图失败时停止诊断
- **WHEN** 截图能力不可用或截图运行失败
- **AND** 用户运行 `star diagnose-screen`
- **THEN** CLI 返回截图诊断错误
- **AND** 系统不执行状态探测

#### Scenario: 状态探测配置错误
- **WHEN** 屏幕截图诊断成功
- **AND** 状态配置非法
- **AND** 用户运行 `star diagnose-screen`
- **THEN** CLI 返回配置错误
- **AND** stderr 输出状态配置错误原因
