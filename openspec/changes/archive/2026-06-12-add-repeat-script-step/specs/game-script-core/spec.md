## MODIFIED Requirements

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
