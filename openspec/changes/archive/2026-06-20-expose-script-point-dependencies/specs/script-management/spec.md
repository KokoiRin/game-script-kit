## ADDED Requirements

### Requirement: 脚本详情暴露点位依赖

系统 SHALL 在脚本详情结果中提供结构化点位依赖列表。该列表 MUST 按脚本阅读顺序收集 `PointRef` 引用并去重；系统 MUST NOT 把裸 `Point(x, y)` 字面量作为点位依赖。

#### Scenario: 收集命名点位依赖
- **WHEN** 命名脚本包含 `Click(PointRef("头像"))`
- **AND** 用户请求脚本详情
- **THEN** 脚本详情结果包含结构化点位依赖 `头像`

#### Scenario: 点位依赖去重
- **WHEN** 命名脚本多次引用 `PointRef("头像")`
- **AND** 用户请求脚本详情
- **THEN** 结构化点位依赖只包含一次 `头像`

#### Scenario: 裸坐标不作为点位依赖
- **WHEN** 命名脚本包含 `Click(Point(100, 200))`
- **AND** 用户请求脚本详情
- **THEN** 结构化点位依赖不包含该裸坐标

### Requirement: CLI 脚本详情展示点位依赖

系统 SHALL 在 `star details <name>` 输出中展示点位依赖分组。CLI MUST 复用 application 层脚本详情结果中的结构化 `point_dependencies`，不得解析步骤文本或通用依赖文本来推导点位依赖。

#### Scenario: CLI 输出点位依赖
- **WHEN** 用户运行 `star details <name>`
- **AND** 脚本详情结果包含点位依赖 `头像`
- **THEN** CLI 输出“点位依赖”分组
- **AND** 该分组包含 `头像`

#### Scenario: 没有点位依赖
- **WHEN** 用户运行 `star details <name>`
- **AND** 脚本详情结果没有点位依赖
- **THEN** CLI 的“点位依赖”分组展示为空
