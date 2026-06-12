## MODIFIED Requirements

### Requirement: Script 由有序动作组成

系统 SHALL 在 `domain.script` 中提供 `Script` 领域模型，用于保存一个稳定脚本名称、一个执行窗口和一组按顺序编排的步骤。脚本步骤可以包含原子动作步骤，也可以包含控制流步骤。

#### Scenario: 创建包含多个步骤的命名脚本

- **WHEN** 调用方使用脚本名称、点击、拖拽、等待和重复步骤创建脚本
- **THEN** 脚本会保留名称，并保留这些步骤的原始顺序

#### Scenario: 脚本绑定单个窗口

- **WHEN** 调用方创建脚本
- **THEN** 脚本会记录一个 `Window`，脚本内所有点击和拖拽步骤默认都在该窗口内执行

#### Scenario: 空脚本被拒绝

- **WHEN** 调用方尝试创建不包含任何步骤的脚本
- **THEN** 系统会拒绝该脚本，并报告脚本至少需要一个步骤

#### Scenario: 空脚本名称被拒绝

- **WHEN** 调用方尝试使用空字符串或只包含空白字符的名称创建脚本
- **THEN** 系统会拒绝该脚本，并报告脚本名称不能为空

### Requirement: Action 支持点击拖拽等待

系统 SHALL 在 `domain.actions` 中定义平台无关的原子动作步骤，包含 `Click`、`Drag` 和 `Wait` 三类动作。系统 MUST 通过 `Step` 类型统一引用脚本可执行步骤，并保留原子动作步骤和控制流步骤的边界。

#### Scenario: 点击动作记录点击点

- **WHEN** 调用方创建 `Click` 动作步骤
- **THEN** 点击动作只记录 `Point`，不记录单独的窗口

#### Scenario: 拖拽动作记录起止点

- **WHEN** 调用方创建 `Drag` 动作步骤
- **THEN** 拖拽动作只记录起点和终点 `Point`，不记录单独的窗口

#### Scenario: 等待动作记录等待时长

- **WHEN** 调用方创建 `Wait` 动作步骤
- **THEN** 等待动作会记录以秒为单位的等待时长

#### Scenario: 动作模型不包含移动动作

- **WHEN** 调用方查看可用原子动作步骤
- **THEN** 系统不会提供独立的移动指针动作

#### Scenario: 点击和拖拽不暴露鼠标按键

- **WHEN** 调用方创建点击或拖拽动作步骤
- **THEN** 动作不要求也不记录左键、右键或中键参数

## ADDED Requirements

### Requirement: Step 支持固定次数重复

系统 SHALL 提供 `Repeat` 步骤，用于按固定次数重复执行一组非空脚本步骤。

#### Scenario: 创建固定次数重复步骤

- **WHEN** 调用方使用正整数次数和非空步骤序列创建 `Repeat`
- **THEN** 系统会保留重复次数和内部步骤序列

#### Scenario: 重复次数必须为正整数

- **WHEN** 调用方使用 0 或负数创建 `Repeat`
- **THEN** 系统会拒绝该重复步骤，并报告重复次数必须大于 0

#### Scenario: 重复步骤必须包含内部步骤

- **WHEN** 调用方创建不包含任何内部步骤的 `Repeat`
- **THEN** 系统会拒绝该重复步骤，并报告重复步骤至少需要一个内部步骤

#### Scenario: 重复步骤允许嵌套

- **WHEN** 调用方在 `Repeat.steps` 中继续放入另一个 `Repeat`
- **THEN** 系统会保留该嵌套步骤树，供 runner 按树结构执行
