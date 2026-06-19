# target-offsets Specification

## Purpose
TBD - created by archiving change add-target-offsets. Update Purpose after archive.
## Requirements
### Requirement: 点位支持 offset
系统 SHALL 支持在基础点位上应用 x/y offset。offset MUST 返回新点位，不得修改原始点位。

#### Scenario: 固定点位应用 offset
- **WHEN** 基础点位为 `Point(242, 92)` 且 offset 为 `x=120, y=-5`
- **THEN** 系统会返回 `Point(362, 87)`

#### Scenario: 原点位保持不变
- **WHEN** 调用方对 `Point(242, 92)` 应用 offset
- **THEN** 原始点位仍为 `Point(242, 92)`

### Requirement: 点击目标支持 offset
系统 SHALL 允许点击目标包装一个基础目标和一个 offset。基础目标可以是固定点位、点位别名或图片目标。

#### Scenario: 命名点位 offset
- **WHEN** `Click` 目标为 `PointRef("头像")` 加 `Point(120, 0)` offset，且 `头像` 解析为 `Point(242, 92)`
- **THEN** runner 会点击 `Point(362, 92)`

#### Scenario: 图片 anchor offset
- **WHEN** `ImageTarget` anchor 为 `right_center`，匹配矩形为 `Rect(10, 20, 30, 40)`，offset 为 `Point(24, 0)`
- **THEN** runner 会点击 `Point(64, 40)`

