## ADDED Requirements

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
