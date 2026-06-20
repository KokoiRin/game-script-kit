## ADDED Requirements

### Requirement: 界面状态探测候选使用图片搜索规格
系统 SHALL 允许界面状态候选使用图片搜索规格表达待匹配图片、搜索区域和最低置信度。候选没有显式搜索区域时 SHALL 继续表示全屏搜索。

#### Scenario: 候选携带搜索区域
- **WHEN** `人物` 状态候选使用图片 `人物.png` 和区域 `右侧面板`
- **THEN** 一轮界面状态探测只在该区域内匹配 `人物.png`

#### Scenario: 旧候选表示全屏搜索
- **WHEN** 系统从 `assets/人物.png` 生成兼容候选
- **THEN** 该候选使用 `人物.png` 和空搜索区域

### Requirement: 界面状态探测支持状态组配置文档
系统 SHALL 支持从 `assets/screen-states.json` 读取界面状态组配置。配置文档 MUST 能声明命名区域、状态组和每个状态组内的图片搜索项。存在该配置文档时，状态探测候选 SHALL 来自配置文档；不存在时，系统 SHALL 回退到扫描 `assets/` 图片文件。

#### Scenario: 从配置文档生成状态组候选
- **WHEN** `assets/screen-states.json` 声明状态 `战斗失败`，并包含 `离开按钮` 与 `重来按钮` 两个搜索项
- **THEN** 界面状态探测会把这两个搜索项作为同一个状态组的候选标识

#### Scenario: 配置文档控制搜索区域
- **WHEN** 配置文档声明 `离开按钮` 使用命名区域 `右上弹窗`
- **THEN** 一轮状态探测会把 `右上弹窗` 解析为该搜索项的搜索区域

#### Scenario: 没有配置文档时回退到 assets 扫描
- **WHEN** `assets/screen-states.json` 不存在
- **THEN** 系统继续把 `assets/` 目录中的支持图片文件作为全屏状态候选

#### Scenario: 非法状态配置被拒绝
- **WHEN** 配置文档引用未知区域、空状态组、空搜索列表或逃逸出 `assets/` 的图片路径
- **THEN** 系统拒绝该配置并返回清晰错误
