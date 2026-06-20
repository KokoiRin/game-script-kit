## ADDED Requirements

### Requirement: 界面状态配置可生成用户摘要
系统 SHALL 支持把 `assets/screen-states.json` 读取为用户可理解的只读配置摘要。摘要 MUST 包含每个状态组的状态名、搜索项名称、图片路径、搜索区域信息和最低置信度。缺少配置文件时，系统 MUST 返回空摘要而不是错误；配置非法时，系统 MUST 返回清晰错误。

#### Scenario: 配置摘要包含状态搜索项
- **WHEN** `assets/screen-states.json` 声明状态 `主页`，并包含搜索项 `主页标识`
- **THEN** 配置摘要包含状态 `主页`
- **AND** 该状态下包含搜索项 `主页标识`、图片路径、区域信息和最低置信度

#### Scenario: 缺少配置时返回空摘要
- **WHEN** `assets/screen-states.json` 不存在
- **THEN** 配置摘要表示没有已配置状态
- **AND** 系统不把缺少配置视为错误

#### Scenario: 非法配置摘要返回错误
- **WHEN** `assets/screen-states.json` 引用不存在图片或非法区域
- **THEN** 系统返回非零摘要结果和清晰错误消息
