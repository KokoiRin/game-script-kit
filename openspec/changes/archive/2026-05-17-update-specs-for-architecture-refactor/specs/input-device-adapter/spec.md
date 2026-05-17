## ADDED Requirements

### Requirement: DryRunInputDevice 提供可观测的假设备

系统 SHALL 在 `adapters.dry_run` 中提供 `DryRunInputDevice`，实现 `engine.ports.InputDevice` 协议，将所有操作记录为可观测的数据结构而不执行真实鼠标操作。

#### Scenario: 记录点击操作

- **WHEN** 调用方通过 `DryRunInputDevice.click(target)` 发起点击
- **THEN** 设备会将操作名 `"click"` 和目标点追加到 `operations` 列表，不移动真实鼠标

#### Scenario: 记录拖拽操作

- **WHEN** 调用方通过 `DryRunInputDevice.drag_to(start, end, duration)` 发起拖拽
- **THEN** 设备会将操作名 `"drag_to"`、起点、终点和持续时间追加到 `operations` 列表

#### Scenario: 操作为不可变记录

- **WHEN** 操作被记录到 `operations` 列表
- **THEN** 每条操作以 `RecordedOperation` dataclass 表达，字段不可变

## MODIFIED Requirements

### Requirement: 输入设备接口支持鼠标指针移动

`engine.ports.InputDevice` 协议 SHALL 定义平台无关的鼠标指针移动操作（作为拖拽的组成部分），用于把指针移动到目标屏幕坐标。

#### Scenario: 移动指针到坐标

- **WHEN** 业务逻辑请求把鼠标指针移动到某个 x/y 坐标
- **THEN** 当前 adapter 会通过 `InputDevice` 接口收到同一个目标坐标

### Requirement: 输入设备接口支持鼠标点击

`engine.ports.InputDevice` 协议 SHALL 定义平台无关的 `click` 操作，用于在目标屏幕坐标执行鼠标点击。

#### Scenario: 在坐标处点击

- **WHEN** 业务逻辑请求在某个 x/y 坐标点击
- **THEN** 当前 adapter 会使用自己的平台专用实现，在该坐标执行鼠标点击

### Requirement: 输入设备接口支持鼠标拖动

`engine.ports.InputDevice` 协议 SHALL 定义平台无关的 `drag_to` 操作，用于以可配置持续时间在两个屏幕坐标之间拖动鼠标指针。

#### Scenario: 在两个坐标之间拖动

- **WHEN** 业务逻辑请求从一个 x/y 坐标拖动到另一个 x/y 坐标
- **THEN** 当前 adapter 会使用自己的平台专用实现，在这些坐标之间执行鼠标拖动

### Requirement: macOS adapter 实现鼠标指针接口

系统 SHALL 在 `adapters.macos` 中提供 macOS Python adapter，实现 `engine.ports.InputDevice` 中的鼠标指针点击和拖动操作。

#### Scenario: macOS adapter 执行鼠标指针操作

- **WHEN** 选择 macOS adapter，且运行环境具备所需权限和依赖
- **THEN** 点击和拖动请求会被转换为 macOS 鼠标指针模拟调用

#### Scenario: macOS adapter 报告 setup 问题

- **WHEN** macOS adapter 因为缺少依赖或权限而无法执行鼠标指针模拟
- **THEN** 它会抛出或报告清晰的 adapter 级错误，并指出 setup 问题

### Requirement: Adapter 实现保持可替换

系统 SHALL 允许在不修改 `domain`、`engine` 或 `scripts_manager` 代码的前提下，增加未来的平台 adapter。

#### Scenario: 执行引擎使用替代 adapter

- **WHEN** 调用方提供 `InputDevice` 的另一个实现（如 `DryRunInputDevice` 或未来平台 adapter）
- **THEN** 现有 `ScriptRunner` 可以通过该实现执行，并且不需要修改代码
