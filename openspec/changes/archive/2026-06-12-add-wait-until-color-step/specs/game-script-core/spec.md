## ADDED Requirements

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
