## ADDED Requirements

### Requirement: CLI 导出界面探测候选裁剪图

系统 SHALL 提供 `star capture-probe-crops` 子命令，用于执行一轮界面状态探测并把每个候选的最佳匹配位置导出为独立裁剪图。CLI MUST 复用 application 层用例，不得在入口层执行截图、裁剪或图片匹配。

#### Scenario: 导出候选裁剪图

- **WHEN** 用户运行 `star capture-probe-crops`
- **THEN** 系统执行一轮界面状态探测
- **AND** 系统保存每个有 `best_rect` 的候选裁剪图
- **AND** CLI 输出每个裁剪图保存路径

#### Scenario: 传递最低置信度

- **WHEN** 用户运行 `star capture-probe-crops --min-confidence 0.75`
- **THEN** 系统使用 `0.75` 作为本次状态探测默认最低置信度

#### Scenario: 没有可裁剪候选

- **WHEN** 本轮状态探测没有任何候选包含 `best_rect`
- **THEN** CLI 返回成功
- **AND** CLI 输出没有保存候选裁剪图

#### Scenario: 候选裁剪失败

- **WHEN** 截图能力、屏幕尺寸或状态探测不可用
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因
