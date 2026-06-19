# screen-image-matching Specification

## Purpose
TBD - created by archiving change add-screen-image-matching-port. Update Purpose after archive.
## Requirements
### Requirement: 图像模板和匹配结果使用领域模型表达
系统 SHALL 在领域层提供平台无关的图像模板和匹配结果模型，用于表达待查找图片、匹配区域、中心点和匹配置信度。

#### Scenario: 创建图像模板
- **WHEN** 调用方使用非空模板图片路径创建图像模板
- **THEN** 系统会保留该模板图片路径

#### Scenario: 空模板路径被拒绝
- **WHEN** 调用方使用空字符串或只包含空白字符的路径创建图像模板
- **THEN** 系统会拒绝该模板并报告模板路径不能为空

#### Scenario: 创建图像匹配结果
- **WHEN** 调用方使用匹配矩形和合法置信度创建图像匹配结果
- **THEN** 系统会保留匹配矩形、置信度，并能提供该矩形的中心点

#### Scenario: 非法匹配置信度被拒绝
- **WHEN** 调用方使用小于 0 或大于 1 的置信度创建图像匹配结果
- **THEN** 系统会拒绝该匹配结果并报告置信度必须在 0 到 1 之间

### Requirement: 业务逻辑通过图像定位端口查找屏幕图片
系统 SHALL 在 `engine.ports` 中提供独立的 `ScreenImageLocator` 端口，用于在当前屏幕或指定区域内查找模板图片。该端口 MUST 独立于 `InputDevice` 和 `PixelColorReader`。

#### Scenario: 查找当前屏幕中的模板图片
- **WHEN** 业务逻辑请求查找某个 `ImageTemplate`
- **THEN** 图像定位端口会接收该模板、可选搜索区域和最低匹配置信度，并返回 `ImageMatch` 或 `None`

#### Scenario: 未找到模板图片
- **WHEN** 当前屏幕或指定区域内不存在满足最低置信度的模板图片
- **THEN** 图像定位端口会返回 `None`，而不是把未找到当作 setup 错误

#### Scenario: 图像定位端口不依赖平台库
- **WHEN** 领域层、engine 层或测试代码引用图像定位能力
- **THEN** 它们依赖 `ScreenImageLocator` 端口，而不是直接导入 `pyautogui`、OpenCV 或 macOS 平台库

#### Scenario: 输入设备端口不承担图像定位职责
- **WHEN** 系统新增屏幕图像匹配能力
- **THEN** `InputDevice` 仍然只提供点击、拖拽和等待能力，不提供图像定位方法

### Requirement: 桌面 adapter 实现屏幕图像匹配
系统 SHALL 提供 macOS 本地运行可用的桌面图像定位 adapter，实现 `ScreenImageLocator` 端口，并隐藏截图、模板读取、平台依赖和权限错误。

#### Scenario: adapter 返回匹配区域和中心点
- **WHEN** adapter 成功在当前屏幕或指定区域内找到模板图片
- **THEN** adapter 会返回包含匹配矩形、中心点和置信度的 `ImageMatch`

#### Scenario: adapter 返回未找到
- **WHEN** adapter 完成截图和匹配但没有找到满足最低置信度的模板图片
- **THEN** adapter 会返回 `None`

#### Scenario: adapter 报告图像匹配 setup 问题
- **WHEN** adapter 因为缺少依赖、模板图片无法读取、截图权限或运行环境限制无法完成匹配
- **THEN** adapter 会抛出清晰的 setup 错误，并提示用户检查依赖、图片路径或屏幕录制权限

#### Scenario: adapter 延迟加载平台依赖
- **WHEN** 只导入业务层、领域层或测试模块
- **THEN** 系统不会因为尚未初始化真实桌面图像定位 adapter 而立即导入或要求平台自动化依赖

### Requirement: 图像匹配能力可在无真实屏幕环境中测试
系统 SHALL 提供 fake 或 dry-run 友好的图像定位实现，使应用层和后续脚本语义可以在不读取真实屏幕的情况下验证图像匹配路径。

#### Scenario: fake locator 返回预设匹配
- **WHEN** 测试替身被配置为对某个模板返回匹配结果
- **THEN** 调用方通过 `ScreenImageLocator` 查找该模板时会收到预设 `ImageMatch`

#### Scenario: fake locator 返回预设未找到
- **WHEN** 测试替身被配置为对某个模板不返回匹配结果
- **THEN** 调用方通过 `ScreenImageLocator` 查找该模板时会收到 `None`
