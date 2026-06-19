## ADDED Requirements

### Requirement: 图片条件和目标支持命名图片
系统 SHALL 允许图片存在条件和图片目标点击使用命名图片引用，同时保持直接使用 `ImageTemplate` 的行为兼容。

#### Scenario: 图片存在条件使用命名图片
- **WHEN** 调用方创建 `ImageExists(ImageRef("开始按钮"))`
- **THEN** 系统会把该条件视为合法条件，并保留名称供执行阶段解析

#### Scenario: 图片目标使用命名图片
- **WHEN** 调用方创建 `ImageTarget(ImageRef("开始按钮"))`
- **THEN** 系统会把该目标视为合法图片目标，并保留名称供执行阶段解析

#### Scenario: 现有图片模板行为保持兼容
- **WHEN** 调用方继续创建 `ImageExists(ImageTemplate(...))` 或 `ImageTarget(ImageTemplate(...))`
- **THEN** 系统会继续把它们视为合法模型
