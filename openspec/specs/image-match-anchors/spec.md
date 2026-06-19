# image-match-anchors Specification

## Purpose
TBD - created by archiving change add-image-match-anchors. Update Purpose after archive.
## Requirements
### Requirement: 匹配结果支持 anchor 点位
系统 SHALL 允许从图片匹配矩形中取得 anchor 点位。anchor MUST 至少支持 `center`、`top_left`、`top_center`、`top_right`、`left_center`、`right_center`、`bottom_left`、`bottom_center` 和 `bottom_right`。

#### Scenario: 取得中心点
- **WHEN** 匹配矩形为 `Rect(10, 20, 30, 40)` 且调用方请求 `center`
- **THEN** 系统会返回 `Point(25, 40)`

#### Scenario: 取得右边中点
- **WHEN** 匹配矩形为 `Rect(10, 20, 30, 40)` 且调用方请求 `right_center`
- **THEN** 系统会返回 `Point(40, 40)`

#### Scenario: 未知 anchor 被拒绝
- **WHEN** 调用方请求不支持的 anchor 名称
- **THEN** 系统会拒绝该请求并报告未知 anchor

