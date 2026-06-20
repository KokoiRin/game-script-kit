## ADDED Requirements

### Requirement: UI 脚本详情展示点位依赖

本地控制 UI SHALL 在脚本详情接口和页面中展示结构化点位依赖。HTTP adapter MUST 只转发 application 层生成的 `point_dependencies` 字段；前端 MUST 使用该字段展示点位依赖，不得解析步骤文本或通用依赖文本。

#### Scenario: HTTP 返回点位依赖
- **WHEN** UI 请求包含 `PointRef("头像")` 的脚本详情
- **THEN** HTTP 响应包含 `point_dependencies`
- **AND** `point_dependencies` 包含 `头像`

#### Scenario: 页面展示点位依赖
- **WHEN** 用户在本地 UI 选择包含点位依赖的脚本
- **THEN** 脚本详情展示“点位依赖”分组
- **AND** 该分组包含点位名称

#### Scenario: 没有点位依赖
- **WHEN** 用户在本地 UI 选择不包含 `PointRef` 的脚本
- **THEN** 脚本详情的“点位依赖”分组展示没有点位依赖
