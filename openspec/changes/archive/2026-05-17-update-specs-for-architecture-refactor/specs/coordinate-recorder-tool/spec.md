## MODIFIED Requirements

### Requirement: 平台 adapter 实现坐标和按键读取

系统 SHALL 通过平台 adapter 实现 `engine.ports.PointerPositionReader` 和 `engine.ports.KeyStateReader` 端口。

#### Scenario: adapter 读取鼠标坐标

- **WHEN** 工具运行在真实平台环境中
- **THEN** 坐标读取 adapter 会读取当前鼠标屏幕坐标并返回 `Point`

#### Scenario: adapter 读取按键状态

- **WHEN** 工具检查 `1`、`Q` 或 `q` 是否按下
- **THEN** 按键状态 adapter 会返回对应按键当前是否处于按下状态

#### Scenario: adapter 按平台边界组织

- **WHEN** 系统提供坐标记录工具所需的真实 adapter
- **THEN** 桌面通用实现会放在 `adapters/desktop/`，macOS 专用实现会放在 `adapters/macos/`

### Requirement: 工具通过坐标读取端口获取坐标

#### Scenario: 工具通过坐标读取端口获取坐标

- **WHEN** 工具需要获取当前鼠标位置
- **THEN** 工具会调用 `PointerPositionReader` 端口，而不是直接调用平台库
