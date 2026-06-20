## ADDED Requirements

### Requirement: 加载项目文件脚本

系统 SHALL 从项目脚本目录加载用户可编辑的 JSON 脚本文件，并把它们合并到可按名称查询的脚本 catalog 中。系统 MUST 保留内置脚本，并 MUST 在脚本名称重复时给出可读错误。

#### Scenario: 列出文件脚本
- **WHEN** 项目脚本目录中存在合法脚本文件 `scripts/打图.json`
- **AND** 用户运行 `star list`
- **THEN** 输出包含脚本名 `打图`

#### Scenario: 内置脚本仍然可用
- **WHEN** 项目脚本目录不存在
- **AND** 用户运行 `star list`
- **THEN** 输出仍然包含内置脚本

#### Scenario: 拒绝重复脚本名称
- **WHEN** 文件脚本名称和内置脚本或另一个文件脚本重复
- **THEN** 系统返回可读错误

### Requirement: 文件脚本 JSON 格式

系统 SHALL 支持用户用 JSON 描述脚本名称、步骤和可选局部资源。文件脚本 MUST 至少支持 `wait`、`click`、`repeat`、`if_state` 和 `wait_until_state` 步骤；系统 MUST 把这些步骤转换为标准 `Script` 领域模型。

#### Scenario: 解析等待和点击步骤
- **WHEN** 文件脚本包含 `wait` 和 `click` 步骤
- **THEN** 脚本详情展示对应等待和点击步骤

#### Scenario: 解析状态分支
- **WHEN** 文件脚本包含 `if_state` 步骤
- **THEN** 脚本详情展示对应 `ScreenStateIs` 状态决策

#### Scenario: 解析状态等待
- **WHEN** 文件脚本包含 `wait_until_state` 步骤
- **THEN** 脚本详情展示对应状态等待

#### Scenario: 拒绝未知步骤
- **WHEN** 文件脚本包含不支持的步骤类型
- **THEN** 系统返回可读错误

### Requirement: 文件脚本复用别名资源

系统 SHALL 允许文件脚本引用点位别名、图片别名、搜索别名、命名区域和界面状态。系统 MUST 复用现有资源合并和依赖检查机制，让 `star details <name>` 能展示文件脚本依赖。

#### Scenario: 引用点位别名
- **WHEN** 文件脚本包含点击点位别名的步骤
- **AND** 用户运行 `star details <name>`
- **THEN** 输出的点位依赖包含该点位名称

#### Scenario: 引用搜索别名
- **WHEN** 文件脚本包含点击搜索别名的步骤
- **AND** 用户运行 `star details <name>`
- **THEN** 输出的图片依赖包含搜索对应的图片

#### Scenario: 引用界面状态
- **WHEN** 文件脚本包含状态分支或状态等待
- **AND** 用户运行 `star details <name>`
- **THEN** 输出展示该状态依赖或状态等待

#### Scenario: 缺失资源可诊断
- **WHEN** 文件脚本引用不存在的图片、区域或搜索别名
- **AND** 用户运行 `star details <name>`
- **THEN** 系统返回可读配置错误或依赖检查结果

### Requirement: 运行文件脚本

系统 SHALL 允许用户通过 `star run <name>` 运行文件脚本。运行路径 MUST 复用现有 dry-run、真实运行、图片定位和界面状态读取能力。

#### Scenario: dry-run 运行文件脚本
- **WHEN** 用户运行 `star run <file-script> --dry-run`
- **THEN** 系统按文件脚本步骤执行 dry-run 并返回成功退出码

#### Scenario: dry-run 使用脚本图片依赖
- **WHEN** 文件脚本引用搜索别名
- **AND** 用户运行 `star run <file-script> --dry-run --dry-run-script-images`
- **THEN** dry-run 图片集合包含文件脚本的图片依赖
