# script-action-model Specification

## Purpose
定义脚本、动作、窗口、点和矩形的核心领域模型（位于 `domain` 包内），以及脚本执行时的坐标解析规则。
## Requirements
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

### Requirement: Window 表达动作坐标所属范围

系统 SHALL 在 `domain.windows` 中定义 `Window` 协议，以及 `ScreenWindow` 和 `AreaWindow` 实现，用于表示脚本内点击和拖拽动作中点坐标所属的坐标范围。

#### Scenario: 屏幕窗口使用屏幕坐标

- **WHEN** 脚本绑定 `ScreenWindow`
- **THEN** 脚本内动作点会被解释为屏幕绝对坐标

#### Scenario: 区域窗口使用区域内坐标

- **WHEN** 脚本绑定 `AreaWindow`
- **THEN** 脚本内动作点会被解释为该区域左上角原点下的区域内坐标

### Requirement: Rect 表达区域窗口范围

系统 SHALL 在 `domain.geometry` 中提供 `Rect` 领域模型，用于记录 `AreaWindow` 在屏幕上的整体范围。

#### Scenario: 区域矩形记录位置和尺寸

- **WHEN** 调用方创建 `AreaWindow`
- **THEN** 区域窗口会通过 `Rect` 记录左上角坐标、宽度和高度

#### Scenario: 非法矩形被拒绝

- **WHEN** 调用方使用非正数宽度或高度创建矩形
- **THEN** 系统会拒绝该矩形

### Requirement: Point 表达点击和拖拽位置

系统 SHALL 在 `domain.geometry` 中提供 `Point` 领域模型，用于表达点击位置以及拖拽起点和终点。

#### Scenario: 点记录二维坐标

- **WHEN** 调用方创建 `Point`
- **THEN** 点会记录 x 和 y 两个坐标值

#### Scenario: 区域窗口解析点为屏幕坐标

- **WHEN** `AreaWindow` 解析一个区域内点
- **THEN** 解析结果会等于区域左上角坐标加上该点坐标

#### Scenario: 屏幕窗口解析点为屏幕坐标

- **WHEN** `ScreenWindow` 解析一个点
- **THEN** 解析结果会保留该点的 x 和 y 坐标

#### Scenario: 坐标解析不做边界夹取

- **WHEN** `AreaWindow` 解析一个位于矩形范围外的点
- **THEN** 解析结果仍然会按区域左上角坐标加上该点坐标计算

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

### Requirement: Condition 支持单点颜色匹配
系统 SHALL 在领域层提供平台无关的条件模型，用于表达脚本运行时可评估的判断。第一版条件模型 MUST 支持单点颜色匹配条件，记录待检测点、期望颜色和每通道容差。

#### Scenario: 创建单点颜色条件
- **WHEN** 调用方使用 `Point`、`Color` 和非负容差创建颜色条件
- **THEN** 条件会保留待检测点、期望颜色和容差

#### Scenario: 颜色条件默认精确匹配
- **WHEN** 调用方创建颜色条件但不提供容差
- **THEN** 条件容差会默认为 0

#### Scenario: 非法颜色容差被拒绝
- **WHEN** 调用方使用小于 0 或大于 255 的容差创建颜色条件
- **THEN** 系统会拒绝该条件，并报告颜色容差必须在 0 到 255 之间

### Requirement: Step 支持条件分支
系统 SHALL 提供 `If` 控制流步骤，用于根据一个条件选择执行一组步骤。`If` MUST 保留条件、非空 `then_steps` 和可为空的 `else_steps`，并通过 `Step` 类型统一引用。

#### Scenario: 创建条件分支步骤
- **WHEN** 调用方使用条件、非空 then 步骤序列和 else 步骤序列创建 `If`
- **THEN** 系统会保留条件和两个分支的步骤序列

#### Scenario: 条件分支 then 步骤必须非空
- **WHEN** 调用方创建不包含任何 then 步骤的 `If`
- **THEN** 系统会拒绝该分支步骤，并报告条件分支至少需要一个 then 步骤

#### Scenario: 条件分支允许省略 else 步骤
- **WHEN** 调用方创建 `If` 时不提供 else 步骤
- **THEN** 系统会把 else 步骤保存为空序列

#### Scenario: 条件分支允许嵌套控制流步骤
- **WHEN** 调用方在 `If` 的分支步骤中放入 `Repeat` 或另一个 `If`
- **THEN** 系统会保留该嵌套步骤树，供 runner 按树结构执行
