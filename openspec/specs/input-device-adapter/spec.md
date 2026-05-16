# input-device-adapter Specification

## Purpose
定义输入设备端口及平台 adapter 的行为边界，使核心 workflow 可以替换不同平台实现。
## Requirements
### Requirement: 输入设备接口支持鼠标指针移动

输入设备接口 SHALL 定义平台无关的鼠标指针移动操作，用于把指针移动到目标屏幕坐标。

#### Scenario: 移动指针到坐标

- **WHEN** 业务逻辑请求把鼠标指针移动到某个 x/y 坐标
- **THEN** 当前 adapter 会通过输入设备接口收到同一个目标坐标

### Requirement: 输入设备接口支持鼠标点击

输入设备接口 SHALL 定义平台无关的点击操作，用于在目标屏幕坐标执行鼠标点击。

#### Scenario: 在坐标处点击

- **WHEN** 业务逻辑请求在某个 x/y 坐标点击
- **THEN** 当前 adapter 会使用自己的平台专用实现，在该坐标执行鼠标点击

### Requirement: 输入设备接口支持鼠标拖动

输入设备接口 SHALL 定义平台无关的拖动操作，用于以可配置持续时间在两个屏幕坐标之间拖动鼠标指针。

#### Scenario: 在两个坐标之间拖动

- **WHEN** 业务逻辑请求从一个 x/y 坐标拖动到另一个 x/y 坐标
- **THEN** 当前 adapter 会使用自己的平台专用实现，在这些坐标之间执行鼠标拖动

### Requirement: macOS adapter 实现鼠标指针接口

系统 SHALL 提供一个 macOS Python adapter，实现输入设备接口中的鼠标指针移动、点击和拖动操作。

#### Scenario: macOS adapter 执行鼠标指针操作

- **WHEN** 选择 macOS adapter，且运行环境具备所需权限和依赖
- **THEN** 移动、点击和拖动请求会被转换为 macOS 鼠标指针模拟调用

#### Scenario: macOS adapter 报告 setup 问题

- **WHEN** macOS adapter 因为缺少依赖或权限而无法执行鼠标指针模拟
- **THEN** 它会抛出或报告清晰的 adapter 级错误，并指出 setup 问题

### Requirement: Adapter 实现保持可替换

系统 SHALL 允许在不修改现有 core workflow 代码的前提下，增加未来的平台 adapter。

#### Scenario: core workflow 使用替代 adapter

- **WHEN** 调用方提供输入设备接口的另一个实现
- **THEN** 现有 core workflow 可以通过该实现执行，并且不需要修改代码
