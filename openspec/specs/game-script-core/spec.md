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

引擎层（`engine.runner.ScriptRunner`）SHALL 将 `domain.Script` 中的步骤树按顺序转换为 `engine.ports.InputDevice` 操作。原子动作步骤会直接映射为设备操作，控制流步骤会由 runner 解释并展开执行其内部步骤。

#### Scenario: runner 按顺序执行脚本步骤

- **WHEN** ScriptRunner 执行包含点击、拖拽、等待和重复步骤的脚本
- **THEN** 它会按照脚本步骤树定义的顺序发起对应操作

#### Scenario: runner 通过 InputDevice 执行点击

- **WHEN** ScriptRunner 执行点击动作步骤
- **THEN** 它会先根据脚本窗口解析点击点，再通过 `InputDevice` 端口发起不带鼠标按键参数的点击

#### Scenario: runner 通过 InputDevice 执行拖拽

- **WHEN** ScriptRunner 执行拖拽动作步骤
- **THEN** 它会先根据脚本窗口解析起点和终点，再通过 `InputDevice` 端口发起不带鼠标按键参数的拖拽

#### Scenario: runner 执行等待动作

- **WHEN** ScriptRunner 执行等待动作步骤
- **THEN** 它会调用 `InputDevice.wait()` 等待动作指定的持续时间，并继续执行后续步骤

#### Scenario: runner 执行固定次数重复步骤

- **WHEN** ScriptRunner 执行 `Repeat(times=3, steps=(Click(...), Wait(...)))`
- **THEN** 它会按内部步骤顺序连续执行 3 轮点击和等待

#### Scenario: runner 执行嵌套重复步骤

- **WHEN** ScriptRunner 执行包含嵌套 `Repeat` 的脚本
- **THEN** 它会递归解释内部步骤，并按嵌套结构展开为最终设备操作顺序

#### Scenario: runner 不执行独立移动动作

- **WHEN** ScriptRunner 执行脚本步骤模型
- **THEN** 它不会把独立移动指针作为脚本步骤处理

#### Scenario: runner 使用脚本级窗口

- **WHEN** ScriptRunner 执行绑定指定区域窗口的脚本
- **THEN** 脚本内所有点击和拖拽步骤都会使用该脚本窗口解析坐标

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
