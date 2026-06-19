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

#### Scenario: adapter 返回可点击坐标系
- **WHEN** adapter 在高分屏或 Retina 屏幕上使用物理像素截图完成匹配
- **THEN** adapter 返回的匹配矩形会转换为鼠标输入 adapter 可点击的屏幕坐标系

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

### Requirement: 桌面 adapter 使用 OpenCV 置信度匹配

桌面图像定位 adapter SHALL use OpenCV-backed template matching so callers can
use `min_confidence` values lower than `1.0` without depending on exact pixel
matching.

#### Scenario: adapter 返回实际最高匹配分数
- **WHEN** adapter 在截图中找到分数大于等于 `min_confidence` 的模板
- **THEN** 它返回 `ImageMatch`，其中 `confidence` 等于 OpenCV 计算出的最高匹配分数

#### Scenario: 最高分低于最低置信度
- **WHEN** adapter 完成截图和模板匹配，但最高匹配分数低于 `min_confidence`
- **THEN** 它返回 `None`

#### Scenario: 模板大于搜索区域
- **WHEN** 模板图片尺寸大于当前截图或指定搜索区域
- **THEN** adapter 返回 `None`，而不是报告 setup 错误

#### Scenario: OpenCV 依赖不可用
- **WHEN** adapter 无法导入 OpenCV 或其数组依赖
- **THEN** 它报告清晰的依赖 setup 错误

### Requirement: 图像定位端口接收解析后的模板
系统 SHALL 在 portable 执行层解析图片别名，`ScreenImageLocator` 端口仍只接收 `ImageTemplate`、可选区域和最低置信度。

#### Scenario: 命名图片解析后调用端口
- **WHEN** 脚本使用命名图片进行图片存在判断或图片点击
- **THEN** 调用 `ScreenImageLocator` 时传入的是解析后的 `ImageTemplate`，而不是图片名称

### Requirement: 未找到图片是查询结果
系统 SHALL 把满足依赖和截图条件但没有找到模板的情况表达为图片匹配查询的未找到结果，而不是平台 setup 错误。

#### Scenario: 查询层收到 None
- **WHEN** `ScreenImageLocator` 返回 `None`
- **THEN** 查询层会返回 found 为假的结果

### Requirement: 图片匹配查询记录耗时日志
图片匹配查询层 SHALL 在调用 `ScreenImageLocator` 时可选记录诊断日志，日志包含模板路径、最低置信度、搜索区域、耗时毫秒、是否命中以及命中置信度。日志能力 MUST 通过可注入端口表达，不得由平台 adapter 直接打印。

#### Scenario: 记录命中耗时
- **WHEN** 图片匹配查询返回命中结果
- **THEN** 日志记录模板路径、耗时毫秒、命中状态和命中置信度

#### Scenario: 记录未命中耗时
- **WHEN** 图片匹配查询返回未命中结果
- **THEN** 日志记录模板路径、耗时毫秒和未命中状态

#### Scenario: 未注入日志端口时行为不变
- **WHEN** 图片匹配查询未注入日志端口
- **THEN** 查询结果和错误语义保持不变

### Requirement: 批量图片定位复用同一张截图
系统 SHALL 提供批量图片定位能力，调用方传入多张模板图片时，真实桌面 adapter MUST 在同一轮批量定位中只截取一次屏幕，并使用这张截图匹配所有模板。

#### Scenario: 批量定位多张模板
- **WHEN** 调用方请求批量定位 `人物.png` 和 `装备.png`
- **THEN** desktop adapter 只执行一次屏幕截图，并返回两张模板各自的匹配结果

#### Scenario: 批量定位保留输入顺序
- **WHEN** 调用方按 `人物.png`、`装备.png` 的顺序请求批量定位
- **THEN** 返回结果按同样顺序对应每个模板

#### Scenario: 批量定位记录阶段耗时
- **WHEN** 调用方为批量定位提供日志器
- **THEN** 系统记录批量匹配的模板数量、截图耗时、总匹配耗时和总耗时

### Requirement: 批量图片定位支持命中即停
系统 SHALL 允许批量图片定位按输入模板顺序命中即停。启用命中即停时，真实桌面 adapter 在找到第一张满足阈值的模板后 MUST 停止匹配后续模板，并在返回结果中把后续模板标记为 skipped。

#### Scenario: 第一个模板命中后停止
- **WHEN** 调用方按 `主页.png`、`人物.png`、`技能.png` 的顺序请求批量定位并启用命中即停
- **AND** `主页.png` 已满足最低置信度
- **THEN** desktop adapter 返回 `主页.png` 的命中结果
- **AND** `人物.png` 与 `技能.png` 的结果标记为 skipped

#### Scenario: 未命中时继续检查全部模板
- **WHEN** 调用方请求批量定位并启用命中即停
- **AND** 当前模板未满足最低置信度
- **THEN** desktop adapter 继续匹配后续模板直到命中或耗尽全部模板

#### Scenario: 日志记录 skipped 数量
- **WHEN** 批量定位启用命中即停并跳过了后续模板
- **THEN** 日志记录本轮模板总数、实际匹配数量和 skipped 数量
