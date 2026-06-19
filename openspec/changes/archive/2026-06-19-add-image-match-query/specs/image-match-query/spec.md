## ADDED Requirements

### Requirement: 图片匹配查询返回显式结果
系统 SHALL 提供平台无关的图片匹配查询结果。查询结果 MUST 表达是否找到图片；找到时 MUST 暴露匹配结果、矩形、中心点和置信度；未找到时 MUST 保留未找到状态。

#### Scenario: 图片匹配查询成功
- **WHEN** 图像定位端口返回 `ImageMatch`
- **THEN** 查询结果会表示 found 为真，并暴露该匹配结果、矩形、中心点和置信度

#### Scenario: 图片匹配查询未找到
- **WHEN** 图像定位端口返回 `None`
- **THEN** 查询结果会表示 found 为假，并且不会把未找到当作 setup 错误

### Requirement: 图片匹配查询解析图片引用
系统 SHALL 在调用 `ScreenImageLocator` 前解析 `ImageTemplate` 或 `ImageRef`。`ScreenImageLocator` MUST 只接收解析后的 `ImageTemplate`。

#### Scenario: 查询命名图片
- **WHEN** 调用方查询 `ImageRef("开始按钮")`
- **THEN** 查询层会通过脚本资源目录解析为 `ImageTemplate` 后调用图像定位端口

#### Scenario: 查询直接模板
- **WHEN** 调用方查询 `ImageTemplate("assets/start.png")`
- **THEN** 查询层会直接使用该模板调用图像定位端口
