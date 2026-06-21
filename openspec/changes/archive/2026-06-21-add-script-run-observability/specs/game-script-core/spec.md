## MODIFIED Requirements

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
