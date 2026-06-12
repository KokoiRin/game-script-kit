## ADDED Requirements

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
