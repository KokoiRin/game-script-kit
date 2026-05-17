# coordinate-recorder-tool Specification

## Purpose
TBD - created by archiving change add-coordinate-recorder-tool. Update Purpose after archive.
## Requirements
### Requirement: 工具实时打印鼠标坐标

系统 SHALL 提供独立坐标记录工具，用于通过坐标读取端口实时读取并打印当前鼠标屏幕坐标。

#### Scenario: 每秒打印当前坐标

- **WHEN** 坐标记录工具正在运行
- **THEN** 工具会每 1 秒打印一次当前鼠标屏幕坐标

#### Scenario: 高频检查按键状态

- **WHEN** 坐标记录工具正在运行
- **THEN** 工具会以短于 1 秒的间隔检查按键状态，默认间隔为 50ms

#### Scenario: 坐标使用 Point 表达

- **WHEN** 工具读取到当前鼠标位置
- **THEN** 工具会用现有 `Point` 模型表达该坐标

#### Scenario: 工具通过坐标读取端口获取坐标

- **WHEN** 工具需要获取当前鼠标位置
- **THEN** 工具会调用坐标读取端口，而不是直接调用平台库

### Requirement: 工具按 1 记录坐标

系统 SHALL 允许用户在坐标记录工具运行时按下 `1` 记录当前鼠标坐标。

#### Scenario: 按 1 记录当前坐标

- **WHEN** 用户按下 `1`
- **THEN** 工具会立即重新读取当前鼠标坐标，并把该坐标追加到本次记录列表

#### Scenario: 长按 1 不重复记录

- **WHEN** 用户持续按住 `1`
- **THEN** 工具只会在按键从未按下变为按下时记录一次坐标

### Requirement: 工具按 Q 结束

系统 SHALL 允许用户在坐标记录工具运行时按下 `Q` 或 `q` 结束工具。

#### Scenario: 按 Q 结束运行

- **WHEN** 用户按下 `Q` 或 `q`
- **THEN** 工具会在下一次按键检测时立即结束运行循环

#### Scenario: 结束后打印所有记录坐标

- **WHEN** 工具结束运行
- **THEN** 工具会打印本次记录的所有坐标

### Requirement: 工具独立于脚本执行流程

系统 SHALL 将坐标记录工具作为独立工具提供，不改变现有脚本执行流程。

#### Scenario: 工具不创建脚本动作

- **WHEN** 用户使用坐标记录工具记录坐标
- **THEN** 工具不会创建或执行 `Script`、`Click`、`Drag` 或 `Wait`

#### Scenario: 工具不新增获取坐标动作

- **WHEN** 系统提供坐标记录能力
- **THEN** 系统不会向脚本动作模型新增 `GetCoordinate` 或同类获取坐标 action

#### Scenario: 工具使用独立入口

- **WHEN** 用户启动坐标记录工具
- **THEN** 用户会通过独立工具入口启动，而不是通过现有 demo CLI 参数启动

### Requirement: 工具报告 setup 问题

系统 SHALL 在鼠标位置读取或键盘状态读取依赖不可用时，报告清晰的 setup 错误。

#### Scenario: 依赖不可用

- **WHEN** 工具因为缺少依赖、权限或运行环境限制无法读取鼠标或键盘
- **THEN** 工具会报告清晰错误，并提示用户检查依赖或权限

#### Scenario: 默认按键 adapter 需要交互终端

- **WHEN** 默认终端按键 adapter 在非交互终端中启动
- **THEN** 工具会报告清晰 setup 错误，而不是尝试使用全局键盘监听

### Requirement: 平台 adapter 实现坐标和按键读取

系统 SHALL 通过平台 adapter 实现坐标读取端口和按键状态读取端口。

#### Scenario: adapter 读取鼠标坐标

- **WHEN** 工具运行在真实平台环境中
- **THEN** 坐标读取 adapter 会读取当前鼠标屏幕坐标并返回 `Point`

#### Scenario: adapter 读取按键状态

- **WHEN** 工具检查 `1`、`Q` 或 `q` 是否按下
- **THEN** 按键状态 adapter 会返回对应按键当前是否处于按下状态

#### Scenario: adapter 按平台边界组织

- **WHEN** 系统提供坐标记录工具所需的真实 adapter
- **THEN** 桌面通用实现会放在 `adapters/desktop/`，macOS 专用实现会放在 `adapters/macos/`

