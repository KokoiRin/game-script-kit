## ADDED Requirements

### Requirement: ImageTarget 支持 anchor
系统 SHALL 允许 `ImageTarget` 指定匹配结果 anchor。anchor 缺省值 MUST 为 `center`，现有图片目标行为保持不变。

#### Scenario: 创建默认 anchor 图片目标
- **WHEN** 调用方创建 `ImageTarget(ImageTemplate(...))`
- **THEN** 图片目标 anchor 为 `center`

#### Scenario: 创建指定 anchor 图片目标
- **WHEN** 调用方创建 `ImageTarget(..., anchor="right_center")`
- **THEN** 图片目标会保留 `right_center`

#### Scenario: 非法 anchor 被拒绝
- **WHEN** 调用方创建带未知 anchor 的 `ImageTarget`
- **THEN** 系统会拒绝该目标并报告未知 anchor
