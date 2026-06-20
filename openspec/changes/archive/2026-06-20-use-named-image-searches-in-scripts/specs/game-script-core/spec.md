## ADDED Requirements

### Requirement: 图片条件支持命名搜索
系统 SHALL 允许 `ImageExists` 使用 `SearchRef` 或 `ImageSearchSpec` 作为图片搜索来源。执行时 MUST 通过脚本资源目录解析搜索规格，并使用解析出的图片、区域和最低置信度执行图片匹配。若 `ImageExists` 显式提供区域或最低置信度，显式值 MUST 覆盖搜索规格中的对应默认值。

#### Scenario: 使用命名搜索判断图片存在
- **WHEN** 脚本资源目录定义搜索 `离开按钮`，指向图片 `assets/离开.png`、区域 `右上弹窗` 和最低置信度 `0.8`
- **AND** 脚本执行 `ImageExists(SearchRef("离开按钮"))`
- **THEN** 系统在区域 `右上弹窗` 内以最低置信度 `0.8` 匹配 `assets/离开.png`

#### Scenario: 图片条件覆盖命名搜索置信度
- **WHEN** 搜索 `离开按钮` 的最低置信度为 `0.8`
- **AND** 脚本执行 `ImageExists(SearchRef("离开按钮"), min_confidence=0.9)`
- **THEN** 系统以最低置信度 `0.9` 执行图片匹配

### Requirement: 图片目标支持命名搜索
系统 SHALL 允许 `ImageTarget` 使用 `SearchRef` 或 `ImageSearchSpec` 作为图片搜索来源。执行点击时 MUST 通过脚本资源目录解析搜索规格，并使用解析出的图片、区域和最低置信度定位图片；定位成功后继续按目标 anchor 和 offset 解析点击点。若 `ImageTarget` 显式提供区域或最低置信度，显式值 MUST 覆盖搜索规格中的对应默认值。

#### Scenario: 点击命名搜索结果
- **WHEN** 脚本资源目录定义搜索 `重来按钮`，指向图片 `assets/重来.png`、区域 `弹窗按钮区` 和最低置信度 `0.8`
- **AND** 脚本执行 `Click(ImageTarget(SearchRef("重来按钮")))`
- **THEN** 系统在区域 `弹窗按钮区` 内以最低置信度 `0.8` 匹配 `assets/重来.png`
- **AND** 系统点击匹配结果的目标点

#### Scenario: 图片目标覆盖命名搜索区域
- **WHEN** 搜索 `重来按钮` 配置了区域 `弹窗按钮区`
- **AND** 脚本执行 `Click(ImageTarget(SearchRef("重来按钮"), region=Rect(10, 20, 30, 40)))`
- **THEN** 系统使用 `Rect(10, 20, 30, 40)` 作为本次图片匹配区域
