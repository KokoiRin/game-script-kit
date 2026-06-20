## ADDED Requirements

### Requirement: 搜索别名可用于脚本图片引用
系统 SHALL 允许脚本图片条件和图片目标引用 `TargetCatalog` 中的命名图片搜索。搜索别名 MUST 解析为图片模板、可选区域和可选最低置信度；引用未知搜索名时，系统 MUST 返回清晰错误。

#### Scenario: 解析搜索别名
- **WHEN** 资源目录定义 `NamedImageSearch("离开按钮", ImageSearchSpec(ImageRef("离开"), RegionRef("弹窗"), 0.8))`
- **AND** 脚本引用 `SearchRef("离开按钮")`
- **THEN** 系统解析出命名图片 `离开` 对应的模板、命名区域 `弹窗` 对应的区域和最低置信度 `0.8`

#### Scenario: 未知搜索别名
- **WHEN** 脚本引用 `SearchRef("缺失搜索")`
- **THEN** 系统报告未知图片搜索名称
