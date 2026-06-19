## ADDED Requirements

### Requirement: Click 支持命名点位目标
系统 SHALL 允许 `Click` 使用命名点位引用作为点击目标。命名点位目标 MUST 保持平台无关，不直接读取屏幕或创建平台 adapter。

#### Scenario: 点击命名点位目标
- **WHEN** 调用方创建 `Click(PointRef("头像"))`
- **THEN** 系统会把该目标视为合法点击目标，并保留名称供执行阶段解析

#### Scenario: 现有固定点点击保持兼容
- **WHEN** 调用方继续创建 `Click(Point(...))`
- **THEN** 系统会继续把它视为合法点击目标
