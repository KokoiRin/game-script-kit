## ADDED Requirements

### Requirement: Click 支持图片目标
系统 SHALL 允许点击动作使用静态 `Point` 或动态 `ImageTarget` 作为目标。静态点点击 MUST 保持既有行为；图片目标 MUST 记录模板图片、可选搜索区域、最低匹配置信度和相对匹配中心点的偏移。

#### Scenario: 创建图片目标
- **WHEN** 调用方使用 `ImageTemplate` 创建 `ImageTarget`
- **THEN** 图片目标会保留模板图片，并使用全屏搜索、默认最低置信度和零偏移

#### Scenario: 创建带区域和偏移的图片目标
- **WHEN** 调用方使用 `ImageTemplate`、`Rect`、最低匹配置信度和 offset 创建 `ImageTarget`
- **THEN** 图片目标会保留这些字段

#### Scenario: 非法图片目标最低匹配置信度被拒绝
- **WHEN** 调用方使用小于等于 0 或大于 1 的最低匹配置信度创建 `ImageTarget`
- **THEN** 系统会拒绝该目标，并报告最低匹配置信度必须大于 0 且不超过 1

#### Scenario: 点击动作保存图片目标
- **WHEN** 调用方创建 `Click(ImageTarget(...))`
- **THEN** 点击动作会保留该图片目标

#### Scenario: 点击动作继续支持静态点
- **WHEN** 调用方创建 `Click(Point(...))`
- **THEN** 点击动作会继续保留该静态点，既有脚本无需修改
