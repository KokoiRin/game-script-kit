## ADDED Requirements

### Requirement: CLI 提供界面状态截图诊断入口

系统 SHALL 提供命令行截图诊断入口，用于帮助用户调试界面状态识别素材和区域。CLI MUST 复用 application 层截图诊断用例，不得在入口层直接截图、绘制区域或解析状态配置。

#### Scenario: 保存当前屏幕截图

- **WHEN** 用户运行 `star capture-screen`
- **THEN** CLI 保存一张当前屏幕截图
- **AND** stdout 输出截图保存路径
- **AND** CLI 返回 application 层用例的退出码

#### Scenario: 保存状态识别区域诊断图

- **WHEN** 用户运行 `star capture-region-diagnostics`
- **THEN** CLI 保存一张带状态识别区域框的诊断截图
- **AND** stdout 输出诊断图保存路径
- **AND** CLI 返回 application 层用例的退出码

#### Scenario: 截图诊断失败

- **WHEN** 截图 adapter 不可用、截图权限缺失、状态配置非法或缺少命名区域
- **AND** 用户运行截图诊断命令
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因
