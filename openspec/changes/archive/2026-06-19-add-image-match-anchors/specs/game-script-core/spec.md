## ADDED Requirements

### Requirement: Runner 点击图片目标 anchor
引擎层 `ScriptRunner` SHALL 在图片目标匹配成功后点击目标指定的 anchor 点位。默认 anchor MUST 保持中心点。

#### Scenario: 点击默认中心点
- **WHEN** `ImageTarget` 未指定 anchor 且匹配矩形为 `Rect(10, 20, 30, 40)`
- **THEN** runner 会点击 `Point(25, 40)`

#### Scenario: 点击右边中点
- **WHEN** `ImageTarget` 指定 `right_center` 且匹配矩形为 `Rect(10, 20, 30, 40)`
- **THEN** runner 会点击 `Point(40, 40)`
