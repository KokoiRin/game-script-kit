## ADDED Requirements

### Requirement: Runner 解析命名图片点击
引擎层 `ScriptRunner` SHALL 在执行图片目标点击前解析命名图片。解析 MUST 使用脚本携带的 portable 资源目录，并继续通过 `ScreenImageLocator` 查找解析后的 `ImageTemplate`。

#### Scenario: 命名图片点击成功
- **WHEN** `Click` 目标引用命名图片 `开始按钮`，且该名称解析为 `ImageTemplate("assets/start.png")`
- **THEN** runner 会用该模板调用图像定位端口并点击匹配中心点

#### Scenario: 未知命名图片点击失败
- **WHEN** `Click` 目标引用未注册的命名图片
- **THEN** runner 会拒绝执行该点击并报告未知图片名称

### Requirement: 条件评估解析命名图片
条件评估 SHALL 在评估图片存在条件前解析命名图片，并继续保持未找到返回假。

#### Scenario: 命名图片存在条件为真
- **WHEN** `ImageExists` 引用命名图片且图像定位端口返回匹配结果
- **THEN** 条件评估结果为真

#### Scenario: 命名图片存在条件为假
- **WHEN** `ImageExists` 引用命名图片且图像定位端口返回 `None`
- **THEN** 条件评估结果为假

#### Scenario: 未知命名图片条件失败
- **WHEN** `ImageExists` 引用未注册的命名图片
- **THEN** 条件评估会拒绝执行并报告未知图片名称

### Requirement: 脚本需求分析识别命名图片
脚本需求分析 SHALL 把命名图片存在条件和命名图片点击目标识别为需要 `ScreenImageLocator` 的脚本能力。

#### Scenario: 命名图片条件需要图像定位端口
- **WHEN** 脚本包含 `ImageExists(ImageRef(...))`
- **THEN** 需求分析结果会标记需要 `ScreenImageLocator`

#### Scenario: 命名图片点击需要图像定位端口
- **WHEN** 脚本包含 `Click(ImageTarget(ImageRef(...)))`
- **THEN** 需求分析结果会标记需要 `ScreenImageLocator`
