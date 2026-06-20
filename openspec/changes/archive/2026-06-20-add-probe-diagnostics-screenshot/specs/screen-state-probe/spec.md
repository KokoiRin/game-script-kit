## ADDED Requirements

### Requirement: CLI 导出界面探测诊断截图

系统 SHALL 提供 `star capture-probe-diagnostics` 子命令，用于执行一轮界面状态探测并保存带候选最佳匹配框的诊断截图。CLI MUST 复用 application 层用例，不得在入口层执行截图、绘图或图片匹配。

#### Scenario: 导出探测诊断截图

- **WHEN** 用户运行 `star capture-probe-diagnostics`
- **THEN** 系统执行一轮界面状态探测
- **AND** 系统保存一张诊断截图
- **AND** 诊断截图包含候选的最佳匹配位置
- **AND** CLI 输出保存路径和当前探测状态

#### Scenario: 传递最低置信度

- **WHEN** 用户运行 `star capture-probe-diagnostics --min-confidence 0.75`
- **THEN** 系统使用 `0.75` 作为本次状态探测默认最低置信度

#### Scenario: 探测诊断截图失败

- **WHEN** 截图能力、屏幕尺寸或状态探测不可用
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因
