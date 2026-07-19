## MODIFIED Requirements

### Requirement: 文件脚本 JSON 格式

系统 SHALL 支持用户用 JSON 描述脚本名称、步骤和可选局部资源。文件脚本 MUST 至少支持 `wait`、`click`、`repeat`、`if_state`、`wait_until_state` 和 `wait_until_image` 步骤；系统 MUST 把这些步骤转换为标准 `Script` 领域模型。

#### Scenario: 解析等待和点击步骤
- **WHEN** 文件脚本包含 `wait` 和 `click` 步骤
- **THEN** 脚本详情展示对应等待和点击步骤

#### Scenario: 解析状态分支
- **WHEN** 文件脚本包含 `if_state` 步骤
- **THEN** 脚本详情展示对应 `ScreenStateIs` 状态决策

#### Scenario: 解析状态等待
- **WHEN** 文件脚本包含 `wait_until_state` 步骤
- **THEN** 脚本详情展示对应状态等待

#### Scenario: 解析图片等待
- **WHEN** 文件脚本包含引用命名搜索的 `wait_until_image` 步骤
- **THEN** 系统把该步骤转换为 `WaitUntil(ImageExists(SearchRef(...)))`
- **AND** 脚本详情展示对应图片依赖

#### Scenario: 拒绝未知步骤
- **WHEN** 文件脚本包含不支持的步骤类型
- **THEN** 系统返回可读错误
