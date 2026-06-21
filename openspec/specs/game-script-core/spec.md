# game-script-core Specification

## Purpose
定义平台无关的游戏自动化业务 workflow 如何通过 `engine.ports.InputDevice` 抽象组织和测试。
## Requirements
### Requirement: 业务逻辑依赖输入设备抽象

游戏自动化业务逻辑 SHALL 通过 `engine.ports.InputDevice` 抽象调用鼠标指针动作，而不是直接调用平台专用的鼠标或键盘 API。领域模型（`domain` 包）和脚本定义（`scripts_manager` 包）不依赖任何平台 adapter。

#### Scenario: workflow 可以使用测试输入设备运行

- **WHEN** demo workflow 使用 `DryRunInputDevice` 或 fake 输入设备实现执行
- **THEN** workflow 会记录预期的鼠标指针操作，并且不需要 macOS 自动化 API

#### Scenario: workflow 不依赖 macOS

- **WHEN** domain 或 engine 模块在非 macOS 或测试环境中被导入
- **THEN** 导入过程不会导入或初始化 macOS 鼠标指针 adapter

### Requirement: Demo workflow 组合可复用动作

系统 SHALL 通过 `scripts_manager` 提供 demo workflow，基于领域动作模型组合多个鼠标指针操作，用来演示游戏脚本逻辑如何与设备行为分离。

#### Scenario: demo workflow 使用注入的设备

- **WHEN** demo workflow 被构造或调用
- **THEN** 调用方可以提供用于执行 workflow 动作的 `InputDevice` 实现

#### Scenario: demo workflow 保持平台无关

- **WHEN** demo workflow 执行移动、点击和拖动行为
- **THEN** 它只通过 `InputDevice` 抽象发起这些动作，不直接依赖平台 adapter

### Requirement: ScriptRunner 无需真实鼠标移动即可测试

系统 SHALL 允许使用 `DryRunInputDevice` 或 fake 输入设备验证 `ScriptRunner` 行为，该设备会捕获 runner 请求的操作而不移动真实鼠标。

#### Scenario: 测试验证操作顺序

- **WHEN** ScriptRunner 使用 fake 输入设备进行测试
- **THEN** 测试可以断言请求的鼠标指针操作顺序和参数

### Requirement: ScriptRunner 执行脚本动作模型

引擎层（`engine.runner.ScriptRunner`）SHALL 将 `domain.Script` 中的动作按顺序转换为 `engine.ports.InputDevice` 操作。系统 MAY 在步骤边界输出运行事件日志，用于说明步骤开始、成功、失败、点击目标解析、等待、Repeat 轮次、If 分支选择和 WaitUntil 轮询结果；这些事件 MUST NOT 改变脚本执行顺序或动作语义。

#### Scenario: runner 按顺序执行脚本动作

- **WHEN** ScriptRunner 执行包含点击、拖拽和等待动作的脚本
- **THEN** 它会按照脚本中的动作顺序发起对应操作

#### Scenario: runner 通过 InputDevice 执行点击

- **WHEN** ScriptRunner 执行点击动作
- **THEN** 它会先根据脚本窗口解析点击点，再通过 `InputDevice` 端口发起不带鼠标按键参数的点击

#### Scenario: runner 通过 InputDevice 执行拖拽

- **WHEN** ScriptRunner 执行拖拽动作
- **THEN** 它会先根据脚本窗口解析起点和终点，再通过 `InputDevice` 端口发起不带鼠标按键参数的拖拽

#### Scenario: runner 执行等待动作

- **WHEN** ScriptRunner 执行等待动作
- **THEN** 它会等待动作指定的持续时间，并继续执行后续动作

#### Scenario: runner 不执行独立移动动作

- **WHEN** ScriptRunner 执行第一版脚本动作模型
- **THEN** 它不会把独立移动指针作为脚本动作处理

#### Scenario: runner 使用脚本级窗口

- **WHEN** ScriptRunner 执行绑定指定区域窗口的脚本
- **THEN** 脚本内所有点击和拖拽动作都会使用该脚本窗口解析坐标

#### Scenario: runner 输出步骤事件

- **WHEN** 调用方启用步骤事件日志并运行脚本
- **THEN** runner 输出步骤开始和步骤成功事件
- **AND** 若某一步抛出运行错误，runner 输出该步骤失败事件并继续向调用方抛出原错误

### Requirement: Demo workflow 基于脚本模型表达

系统 SHALL 允许 `scripts_manager` 中的 demo workflow 通过 `domain.Script` 步骤模型表达固定动作序列。

#### Scenario: demo workflow 构造脚本

- **WHEN** 调用方运行 demo workflow
- **THEN** demo workflow 构造包含点击、拖拽和等待步骤的 `Script`，并交由 `ScriptRunner` 执行

#### Scenario: demo workflow 保持 adapter 无关

- **WHEN** demo workflow 通过脚本模型执行
- **THEN** 它仍然只依赖 `InputDevice` 抽象，不会直接导入或初始化平台 adapter

### Requirement: ScriptRunner 执行条件分支步骤
引擎层 `ScriptRunner` SHALL 解释 `If` 条件分支步骤，根据条件评估结果递归执行 then 分支或 else 分支。runner MUST 通过端口读取运行时屏幕状态，不得让领域模型或脚本定义直接依赖平台 adapter。

#### Scenario: runner 执行 then 分支
- **WHEN** ScriptRunner 执行颜色条件结果为真的 `If`
- **THEN** 它会按顺序执行 `then_steps`，并且不会执行 `else_steps`

#### Scenario: runner 执行 else 分支
- **WHEN** ScriptRunner 执行颜色条件结果为假的 `If`
- **THEN** 它会按顺序执行 `else_steps`，并且不会执行 `then_steps`

#### Scenario: runner 跳过空 else 分支
- **WHEN** ScriptRunner 执行颜色条件结果为假且 `else_steps` 为空的 `If`
- **THEN** 它不会发起该分支内的设备操作，并继续执行后续脚本步骤

#### Scenario: runner 评估颜色条件时解析脚本窗口
- **WHEN** ScriptRunner 在绑定区域窗口的脚本内评估颜色条件
- **THEN** 它会先使用脚本窗口解析条件点，再把解析后的屏幕坐标交给颜色读取端口

#### Scenario: runner 使用颜色容差评估条件
- **WHEN** ScriptRunner 读取到的颜色每个 RGB 通道都与期望颜色相差不超过条件容差
- **THEN** 颜色条件评估为真

#### Scenario: runner 缺少颜色读取端口时报错
- **WHEN** ScriptRunner 执行包含颜色条件的脚本但未注入颜色读取端口
- **THEN** 它会拒绝执行该条件并报告颜色读取端口缺失

#### Scenario: runner 支持嵌套条件分支和重复步骤
- **WHEN** ScriptRunner 执行包含嵌套 `If` 和 `Repeat` 的步骤树
- **THEN** 它会按步骤树结构递归解释控制流，并保持原有窗口坐标解析规则

### Requirement: ScriptRunner 执行条件等待步骤
引擎层 `ScriptRunner` SHALL 解释 `WaitUntil` 条件等待步骤，在条件满足前按轮询间隔等待，并在超时前条件变为真时继续执行后续步骤。runner MUST 通过条件评估模块评估条件，并通过 `InputDevice.wait()` 表达等待。

#### Scenario: 条件初始满足时立即继续
- **WHEN** ScriptRunner 执行条件初始结果为真的 `WaitUntil`
- **THEN** 它不会调用 `InputDevice.wait()`，并会继续执行后续步骤

#### Scenario: 条件等待后满足
- **WHEN** ScriptRunner 执行条件初始为假但在超时前变为真的 `WaitUntil`
- **THEN** 它会按轮询间隔调用 `InputDevice.wait()`，并在条件满足后继续执行后续步骤

#### Scenario: 条件等待超时
- **WHEN** ScriptRunner 执行 `WaitUntil` 且条件在超时时间内始终为假
- **THEN** 它会抛出条件等待超时错误，并不会执行后续脚本步骤

#### Scenario: 条件等待不超过剩余超时预算
- **WHEN** `WaitUntil` 的剩余超时时间小于轮询间隔
- **THEN** runner 会按剩余超时时间调用 `InputDevice.wait()`，而不是等待完整轮询间隔

#### Scenario: 条件等待使用脚本窗口和颜色读取端口
- **WHEN** ScriptRunner 执行使用颜色条件的 `WaitUntil`
- **THEN** 条件评估模块会使用脚本窗口解析条件点，并通过颜色读取端口读取屏幕颜色

#### Scenario: 条件等待支持嵌套控制流
- **WHEN** ScriptRunner 执行包含 `WaitUntil`、`If` 和 `Repeat` 的嵌套步骤树
- **THEN** 它会按步骤树结构递归解释控制流，并保持原有窗口坐标解析规则

### Requirement: ScriptRunner 评估图片存在条件
引擎层 `ScriptRunner` SHALL 支持通过 `ScreenImageLocator` 端口评估 `ImageExists` 条件。runner MUST 保持平台无关，不得直接导入或初始化桌面图像匹配 adapter。

#### Scenario: 图片存在条件为真
- **WHEN** `ScreenImageLocator` 对 `ImageExists.template` 返回满足最低置信度的 `ImageMatch`
- **THEN** 条件评估结果为真

#### Scenario: 图片存在条件为假
- **WHEN** `ScreenImageLocator` 对 `ImageExists.template` 返回 `None`
- **THEN** 条件评估结果为假

#### Scenario: 图片存在条件解析搜索区域
- **WHEN** ScriptRunner 在绑定区域窗口的脚本内评估带 `region` 的 `ImageExists`
- **THEN** 条件评估模块会先使用脚本窗口解析搜索区域左上角，再把解析后的屏幕区域交给图像定位端口

#### Scenario: 图片存在条件传递最低匹配置信度
- **WHEN** ScriptRunner 评估带最低匹配置信度的 `ImageExists`
- **THEN** 条件评估模块会把该最低匹配置信度传给 `ScreenImageLocator`

#### Scenario: 缺少图像定位端口时报错
- **WHEN** ScriptRunner 执行包含图片存在条件的脚本但未注入图像定位端口
- **THEN** 它会拒绝执行该条件并报告图像定位端口缺失

#### Scenario: 条件分支使用图片存在条件
- **WHEN** ScriptRunner 执行图片存在条件结果为真的 `If`
- **THEN** 它会按现有条件分支语义执行 `then_steps`

#### Scenario: 条件等待使用图片存在条件
- **WHEN** ScriptRunner 执行图片存在条件初始为假但在超时前变为真的 `WaitUntil`
- **THEN** 它会按现有条件等待语义轮询并在条件满足后继续执行后续步骤

### Requirement: ScriptRunner 评估界面状态条件
引擎层 `ScriptRunner` SHALL 支持通过 `ScreenStateReader` 端口评估 `ScreenStateIs` 条件。runner MUST 保持平台无关，不得直接读取状态配置文件、启动 UI 或创建桌面图像匹配 adapter。外层 application MAY 提供带缓存策略的 `ScreenStateReader` 实现。

#### Scenario: 界面状态条件为真
- **WHEN** `ScreenStateReader` 返回当前状态 `主页`
- **AND** ScriptRunner 评估 `ScreenStateIs("主页")`
- **THEN** 条件评估结果为真

#### Scenario: 界面状态条件为假
- **WHEN** `ScreenStateReader` 返回当前状态 `人物`
- **AND** ScriptRunner 评估 `ScreenStateIs("主页")`
- **THEN** 条件评估结果为假

#### Scenario: 界面状态条件传递最低置信度
- **WHEN** ScriptRunner 评估带最低置信度的 `ScreenStateIs`
- **THEN** 条件评估模块会把该最低置信度传给 `ScreenStateReader`

#### Scenario: 缺少界面状态读取端口时报错
- **WHEN** ScriptRunner 执行包含界面状态条件的脚本但未注入界面状态读取端口
- **THEN** 它会拒绝执行该条件并报告界面状态读取端口缺失

#### Scenario: 条件分支使用界面状态条件
- **WHEN** ScriptRunner 执行界面状态条件结果为真的 `If`
- **THEN** 它会按现有条件分支语义执行 `then_steps`

#### Scenario: 条件等待使用界面状态条件
- **WHEN** ScriptRunner 执行界面状态条件初始为假但在超时前变为真的 `WaitUntil`
- **THEN** 它会按现有条件等待语义轮询并在条件满足后继续执行后续步骤

### Requirement: ScriptRunner 执行图片目标点击
引擎层 `ScriptRunner` SHALL 支持执行 `Click(ImageTarget(...))`。runner MUST 通过 `ScreenImageLocator` 端口解析图片目标，并在得到最终屏幕坐标后继续通过 `InputDevice.click()` 执行点击。

#### Scenario: 图片目标点击匹配中心点
- **WHEN** `ScreenImageLocator` 对 `ImageTarget.template` 返回 `ImageMatch`
- **THEN** runner 会点击该匹配结果的中心点

#### Scenario: 图片目标点击应用 offset
- **WHEN** `ImageTarget` 设置了 offset
- **THEN** runner 会点击匹配中心点加 offset 后的屏幕坐标

#### Scenario: 图片目标点击解析搜索区域
- **WHEN** ScriptRunner 在绑定区域窗口的脚本内执行带 `region` 的 `Click(ImageTarget(...))`
- **THEN** runner 会先使用脚本窗口解析搜索区域左上角，再把解析后的屏幕区域交给图像定位端口

#### Scenario: 图片目标点击传递最低匹配置信度
- **WHEN** ScriptRunner 执行带最低匹配置信度的 `Click(ImageTarget(...))`
- **THEN** runner 会把该最低匹配置信度传给 `ScreenImageLocator`

#### Scenario: 图片目标未找到时报错
- **WHEN** `ScreenImageLocator` 对 `ImageTarget.template` 返回 `None`
- **THEN** runner 会拒绝执行该点击并报告图片目标未找到

#### Scenario: 缺少图像定位端口时报错
- **WHEN** ScriptRunner 执行 `Click(ImageTarget(...))` 但未注入图像定位端口
- **THEN** runner 会拒绝执行该点击并报告图像定位端口缺失

#### Scenario: 静态点点击行为保持不变
- **WHEN** ScriptRunner 执行 `Click(Point(...))`
- **THEN** runner 会继续按脚本窗口解析静态点并调用 `InputDevice.click()`

### Requirement: Runner 解析命名点位点击
引擎层 `ScriptRunner` SHALL 在执行点击前解析命名点位目标。解析 MUST 使用脚本携带的 portable 资源目录，不得直接依赖平台 adapter。

#### Scenario: 命名点位点击成功
- **WHEN** `Click` 目标引用命名点位 `头像`，且该名称解析为 `Point(242, 92)`
- **THEN** runner 会点击 `Point(242, 92)`

#### Scenario: 命名点位点击应用脚本窗口
- **WHEN** 脚本绑定 `AreaWindow` 且 `Click` 目标引用命名点位
- **THEN** runner 会按现有窗口规则把点位解析为屏幕坐标后再点击

#### Scenario: 未知命名点位点击失败
- **WHEN** `Click` 目标引用未注册的命名点位
- **THEN** runner 会拒绝执行该点击并报告未知点位名称

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

### Requirement: 条件和点击复用图片匹配查询
引擎层 SHALL 通过统一图片匹配查询层评估图片存在条件和解析图片点击目标。查询层 MUST 继续使用已注入的 `ScreenImageLocator`，不得创建平台 adapter。

#### Scenario: 图片存在条件消费查询结果
- **WHEN** 图片匹配查询返回 found 为真
- **THEN** 图片存在条件评估为真

#### Scenario: 图片目标点击消费查询结果
- **WHEN** 图片匹配查询返回 `ImageMatch`
- **THEN** 图片目标点击会继续使用匹配中心点作为点击点

#### Scenario: 图片目标未找到仍报错
- **WHEN** 图片匹配查询返回 found 为假
- **THEN** 图片目标点击会拒绝执行并报告图片目标未找到

### Requirement: Runner 点击图片目标 anchor
引擎层 `ScriptRunner` SHALL 在图片目标匹配成功后点击目标指定的 anchor 点位。默认 anchor MUST 保持中心点。

#### Scenario: 点击默认中心点
- **WHEN** `ImageTarget` 未指定 anchor 且匹配矩形为 `Rect(10, 20, 30, 40)`
- **THEN** runner 会点击 `Point(25, 40)`

#### Scenario: 点击右边中点
- **WHEN** `ImageTarget` 指定 `right_center` 且匹配矩形为 `Rect(10, 20, 30, 40)`
- **THEN** runner 会点击 `Point(40, 40)`

### Requirement: Runner 解析偏移点击目标
引擎层 `ScriptRunner` SHALL 先解析偏移目标的基础目标，再应用 offset，最终通过 `InputDevice.click()` 点击结果点。

#### Scenario: 固定点位 offset 点击
- **WHEN** `Click` 目标为 `Point(10, 20)` 加 `Point(5, -3)` offset
- **THEN** runner 会点击 `Point(15, 17)`

#### Scenario: 命名点位 offset 点击
- **WHEN** `Click` 目标为 `PointRef("头像")` 加 `Point(120, 0)` offset，且名称解析为 `Point(242, 92)`
- **THEN** runner 会点击 `Point(362, 92)`

#### Scenario: 图片目标 offset 在 anchor 后应用
- **WHEN** 图片目标 anchor 为 `right_center`，匹配矩形为 `Rect(10, 20, 30, 40)`，offset 为 `Point(24, 0)`
- **THEN** runner 会点击 `Point(64, 40)`

### Requirement: ScriptRunner 支持取消运行
引擎层 `ScriptRunner` SHALL 支持可选取消检查；当取消信号被置位时，runner MUST 停止执行后续脚本步骤并报告脚本运行已取消。取消机制 MUST 通过可注入端口表达，不得依赖 UI、HTTP 或平台 adapter。

#### Scenario: 重复步骤中取消
- **WHEN** ScriptRunner 执行 `Repeat` 时取消信号变为已取消
- **THEN** runner 停止后续轮次和步骤，并报告运行已取消

#### Scenario: 等待前后检查取消
- **WHEN** ScriptRunner 执行等待步骤前或等待返回后发现取消信号
- **THEN** runner 停止后续脚本步骤，并报告运行已取消

#### Scenario: 未注入取消检查时行为不变
- **WHEN** ScriptRunner 未注入取消检查
- **THEN** runner 按现有语义完整执行脚本

### Requirement: ScriptRunner 记录界面状态条件评估日志
引擎层 SHALL 在评估 `ScreenStateIs` 条件时通过已注入的运行日志端口记录评估摘要。日志 MUST 包含期望状态、实际状态、最低置信度和条件是否匹配。未注入日志端口时，系统 MUST 保持现有条件评估行为且不报错。

#### Scenario: 状态条件命中时记录日志
- **WHEN** ScriptRunner 评估 `ScreenStateIs("主页")`
- **AND** `ScreenStateReader` 返回当前状态 `主页`
- **THEN** 运行日志包含期望状态 `主页`、实际状态 `主页` 和匹配结果 `True`

#### Scenario: 状态条件未命中时记录日志
- **WHEN** ScriptRunner 评估 `ScreenStateIs("主页")`
- **AND** `ScreenStateReader` 返回当前状态 `人物`
- **THEN** 运行日志包含期望状态 `主页`、实际状态 `人物` 和匹配结果 `False`

#### Scenario: 没有日志端口时保持静默
- **WHEN** 条件评估调用未注入运行日志端口
- **THEN** `ScreenStateIs` 条件继续按当前状态返回布尔结果

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
