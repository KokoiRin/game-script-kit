## ADDED Requirements

### Requirement: 截图诊断暴露疑似全黑截图警告

系统 SHALL 在截图诊断类用例保存截图后检查截图是否疑似全黑。若截图疑似全黑，系统 MUST 保留已保存截图，并在 application 结果中返回用户可见警告，提示用户检查屏幕录制权限、前台窗口或运行会话。

#### Scenario: 保存当前屏幕时提示疑似全黑

- **WHEN** 用户运行 `star capture-screen`
- **AND** 保存的截图疑似全黑
- **THEN** CLI 返回 application 层用例的退出码
- **AND** stderr 输出疑似全黑截图警告
- **AND** stdout 仍输出截图保存路径

#### Scenario: 生成状态诊断图时提示疑似全黑

- **WHEN** 用户运行截图诊断或裁剪导出命令
- **AND** 本次保存的原始截图疑似全黑
- **THEN** CLI 返回 application 层用例的退出码
- **AND** stderr 输出疑似全黑截图警告
- **AND** 系统仍按原命令语义保存可生成的诊断文件

#### Scenario: 正常截图不输出警告

- **WHEN** 用户运行截图诊断命令
- **AND** 保存的截图不是疑似全黑
- **THEN** stderr 不包含疑似全黑截图警告
