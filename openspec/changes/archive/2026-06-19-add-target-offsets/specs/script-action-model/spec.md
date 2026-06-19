## ADDED Requirements

### Requirement: Click 支持偏移目标
系统 SHALL 允许 `Click` 使用 `OffsetTarget` 作为点击目标。偏移目标 MUST 保留基础目标和 offset。

#### Scenario: 创建命名点位偏移目标
- **WHEN** 调用方创建基于 `PointRef("头像")` 和 `Point(120, 0)` 的偏移目标
- **THEN** 系统会保留基础目标和 offset

#### Scenario: 现有点击目标保持兼容
- **WHEN** 调用方继续创建 `Click(Point(...))`、`Click(PointRef(...))` 或 `Click(ImageTarget(...))`
- **THEN** 系统会继续把它们视为合法点击目标
