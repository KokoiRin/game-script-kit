# input-device-adapter Specification

## Purpose
定义 `engine.ports` 中的输入设备端口，以及平台 adapter 和 `DryRunInputDevice` 的行为边界，使执行引擎可以替换不同平台实现。

## Requirements
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

### Requirement: 输入设备接口支持等待

`engine.ports.InputDevice` 协议 SHALL 定义平台无关的 `wait` 操作，用于暂停执行指定秒数。

#### Scenario: 等待指定时长

- **WHEN** 业务逻辑请求等待指定秒数
- **THEN** 当前 adapter 会执行对应时长的等待

### Requirement: macOS adapter 实现 InputDevice

系统 SHALL 在 `adapters.macos` 中提供 `MacOSPointerDevice`，实现 `engine.ports.InputDevice` 中的鼠标指针点击、拖动和等待操作。

#### Scenario: macOS adapter 执行鼠标指针操作

- **WHEN** 选择 macOS adapter，且运行环境具备所需权限和依赖
- **THEN** 点击和拖动请求会被转换为 macOS 鼠标指针模拟调用

#### Scenario: macOS adapter 报告 setup 问题

- **WHEN** macOS adapter 因为缺少依赖或权限而无法执行鼠标指针模拟
- **THEN** 它会抛出或报告清晰的 adapter 级错误，并指出 setup 问题

### Requirement: DryRunInputDevice 提供可观测的假设备

系统 SHALL 在 `adapters.dry_run` 中提供 `DryRunInputDevice`，实现 `engine.ports.InputDevice` 协议，将所有操作即时打印为人类可读的输出而不执行真实鼠标操作。

#### Scenario: 即时打印点击操作

- **WHEN** 调用方通过 `DryRunInputDevice.click(target)` 发起点击
- **THEN** 设备会立即打印点击操作和目标坐标，不移动真实鼠标

#### Scenario: 即时打印拖拽操作

- **WHEN** 调用方通过 `DryRunInputDevice.drag_to(start, end, duration)` 发起拖拽
- **THEN** 设备会立即打印拖拽操作的起点、终点和持续时间

#### Scenario: 即时打印等待操作

- **WHEN** 调用方通过 `DryRunInputDevice.wait(duration_seconds)` 发起等待
- **THEN** 设备会立即打印等待时长，不实际休眠

### Requirement: Adapter 实现保持可替换

系统 SHALL 允许在不修改 `domain`、`engine` 或 `scripts_manager` 代码的前提下，增加未来的平台 adapter。

#### Scenario: 执行引擎使用替代 adapter

- **WHEN** 调用方提供 `InputDevice` 的另一个实现（如 `DryRunInputDevice` 或未来平台 adapter）
- **THEN** 现有 `ScriptRunner` 可以通过该实现执行，并且不需要修改代码
