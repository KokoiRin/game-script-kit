## ADDED Requirements

### Requirement: Condition 支持图片存在匹配
系统 SHALL 在领域层提供平台无关的图片存在条件模型，用于表达脚本运行时需要判断某个模板图片是否出现在屏幕或指定区域内。图片存在条件 MUST 记录模板图片、可选搜索区域和最低匹配置信度。

#### Scenario: 创建图片存在条件
- **WHEN** 调用方使用 `ImageTemplate` 创建 `ImageExists`
- **THEN** 条件会保留模板图片，并使用全屏搜索和默认最低置信度

#### Scenario: 创建带区域的图片存在条件
- **WHEN** 调用方使用 `ImageTemplate`、`Rect` 和最低匹配置信度创建 `ImageExists`
- **THEN** 条件会保留模板图片、搜索区域和最低匹配置信度

#### Scenario: 非法最低匹配置信度被拒绝
- **WHEN** 调用方使用小于等于 0 或大于 1 的最低匹配置信度创建 `ImageExists`
- **THEN** 系统会拒绝该条件，并报告最低匹配置信度必须大于 0 且不超过 1

#### Scenario: 条件类型包含图片存在条件
- **WHEN** 调用方在 `If` 或 `WaitUntil` 中使用 `ImageExists`
- **THEN** 系统会把它视为合法 `Condition`
