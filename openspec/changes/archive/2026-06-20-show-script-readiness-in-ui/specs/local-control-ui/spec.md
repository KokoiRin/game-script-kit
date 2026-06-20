## ADDED Requirements

### Requirement: UI 展示脚本依赖检查结果
本地控制 UI SHALL 在脚本详情中展示运行前依赖检查结果。检查结果 MUST 由 application 层生成，HTTP adapter 和前端不得直接读取项目文件或解析状态配置。

#### Scenario: 图片依赖存在
- **WHEN** 选中脚本依赖图片 `assets/start.png`
- **AND** 该文件存在且后缀受支持
- **THEN** 脚本详情展示该图片依赖状态为可用

#### Scenario: 图片依赖缺失
- **WHEN** 选中脚本依赖图片 `assets/start.png`
- **AND** 该文件不存在
- **THEN** 脚本详情展示该图片依赖状态为缺失

#### Scenario: 状态依赖已配置
- **WHEN** 选中脚本依赖界面状态 `主页`
- **AND** 状态配置中存在 `主页`
- **THEN** 脚本详情展示该状态依赖状态为可用

#### Scenario: 状态依赖无法确认
- **WHEN** 选中脚本依赖界面状态 `主页`
- **AND** 状态配置不存在或无法读取
- **THEN** 脚本详情展示该状态依赖状态为无法确认
