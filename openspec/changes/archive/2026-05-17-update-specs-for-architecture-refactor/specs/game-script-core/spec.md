## MODIFIED Requirements

### Requirement: 业务逻辑依赖输入设备抽象

游戏自动化业务逻辑 SHALL 通过 `engine.ports.InputDevice` 抽象调用鼠标指针动作，而不是直接调用平台专用的鼠标或键盘 API。领域模型（`domain` 包）和脚本定义（`scripts_manager` 包）不依赖任何平台 adapter。

#### Scenario: workflow 可以使用测试输入设备运行

- **WHEN** demo workflow 使用 DryRunInputDevice 或 fake 输入设备实现执行
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

系统 SHALL 允许使用 `DryRunInputDevice` 验证 `ScriptRunner` 行为，该设备会捕获 runner 请求的操作而不移动真实鼠标。

#### Scenario: 测试验证操作顺序

- **WHEN** ScriptRunner 使用 DryRunInputDevice 进行测试
- **THEN** 测试可以断言请求的鼠标指针操作顺序和参数

### Requirement: ScriptRunner 执行脚本动作模型

引擎层（`engine.runner.ScriptRunner`）SHALL 将 `domain.Script` 中的动作按顺序转换为 `engine.ports.InputDevice` 操作。

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

### Requirement: Demo workflow 基于脚本模型表达

系统 SHALL 允许 `scripts_manager` 中的 demo workflow 通过 `domain.Script` 动作模型表达固定动作序列。

#### Scenario: demo workflow 构造脚本

- **WHEN** 调用方运行 demo workflow
- **THEN** demo workflow 构造包含点击、拖拽和等待动作的 `Script`，并交由 `ScriptRunner` 执行

#### Scenario: demo workflow 保持 adapter 无关

- **WHEN** demo workflow 通过脚本模型执行
- **THEN** 它仍然只依赖 `InputDevice` 抽象，不会直接导入或初始化平台 adapter
