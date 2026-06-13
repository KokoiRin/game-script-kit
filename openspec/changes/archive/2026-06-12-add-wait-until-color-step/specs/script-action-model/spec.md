## ADDED Requirements

### Requirement: Step 支持条件等待
系统 SHALL 提供 `WaitUntil` 控制流步骤，用于等待一个条件在超时时间内变为真。`WaitUntil` MUST 保留条件、正数超时时间和正数轮询间隔，并通过 `Step` 类型统一引用。

#### Scenario: 创建条件等待步骤
- **WHEN** 调用方使用条件、正数超时时间和正数轮询间隔创建 `WaitUntil`
- **THEN** 系统会保留条件、超时时间和轮询间隔

#### Scenario: 条件等待超时时间必须为正数
- **WHEN** 调用方使用 0 或负数超时时间创建 `WaitUntil`
- **THEN** 系统会拒绝该步骤，并报告条件等待超时时间必须大于 0

#### Scenario: 条件等待轮询间隔必须为正数
- **WHEN** 调用方使用 0 或负数轮询间隔创建 `WaitUntil`
- **THEN** 系统会拒绝该步骤，并报告条件等待轮询间隔必须大于 0

#### Scenario: 条件等待允许嵌套在控制流中
- **WHEN** 调用方在 `Repeat` 或 `If` 的内部步骤中放入 `WaitUntil`
- **THEN** 系统会保留该嵌套步骤树，供 runner 按树结构执行
