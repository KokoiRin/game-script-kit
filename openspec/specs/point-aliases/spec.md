# point-aliases Specification

## Purpose
TBD - created by archiving change add-point-aliases. Update Purpose after archive.
## Requirements
### Requirement: 脚本支持命名点位
系统 SHALL 提供平台无关的命名点位模型，使脚本可以通过稳定名称引用固定 `Point`。命名点位 MUST 保留名称和值，并拒绝空名称。

#### Scenario: 创建命名点位
- **WHEN** 调用方使用名称 `头像` 和 `Point(242, 92)` 创建命名点位
- **THEN** 系统会保留该名称和值，并允许脚本把该名称解析为对应点位

#### Scenario: 空点位名称被拒绝
- **WHEN** 调用方使用空字符串或只包含空白字符的名称创建命名点位
- **THEN** 系统会拒绝该点位并报告名称不能为空

#### Scenario: 未知点位名称报错
- **WHEN** 脚本解析未注册的点位名称
- **THEN** 系统会拒绝解析并报告未知点位名称

