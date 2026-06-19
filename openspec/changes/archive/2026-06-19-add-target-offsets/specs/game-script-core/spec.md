## ADDED Requirements

### Requirement: Runner 解析偏移点击目标
引擎层 `ScriptRunner` SHALL 先解析偏移目标的基础目标，再应用 offset，最终通过 `InputDevice.click()` 点击结果点。

#### Scenario: 固定点位 offset 点击
- **WHEN** `Click` 目标为 `Point(10, 20)` 加 `Point(5, -3)` offset
- **THEN** runner 会点击 `Point(15, 17)`

#### Scenario: 命名点位 offset 点击
- **WHEN** `Click` 目标为 `PointRef("头像")` 加 `Point(120, 0)` offset，且名称解析为 `Point(242, 92)`
- **THEN** runner 会点击 `Point(362, 92)`

#### Scenario: 图片目标 offset 在 anchor 后应用
- **WHEN** 图片目标 anchor 为 `right_center`，匹配矩形为 `Rect(10, 20, 30, 40)`，offset 为 `Point(24, 0)`
- **THEN** runner 会点击 `Point(64, 40)`
