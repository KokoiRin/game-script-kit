## MODIFIED Requirements

### Requirement: Window 表达动作坐标所属范围

系统 SHALL 在 `domain.windows` 中定义 `Window` 协议，以及 `ScreenWindow` 和 `AreaWindow` 实现，用于表示脚本内动作点坐标和图片搜索区域所属的坐标范围。

#### Scenario: 屏幕窗口使用屏幕坐标

- **WHEN** 脚本绑定 `ScreenWindow`
- **THEN** 脚本内动作点会被解释为屏幕绝对坐标

#### Scenario: 区域窗口使用区域内坐标

- **WHEN** 脚本绑定 `AreaWindow`
- **THEN** 脚本内动作点会被解释为该区域左上角原点下的区域内坐标

#### Scenario: 屏幕窗口默认搜索整屏

- **WHEN** `ScreenWindow` 解析未指定的图片搜索区域
- **THEN** 结果为 `None`，表示保持整屏搜索

#### Scenario: 区域窗口默认搜索自身范围

- **WHEN** `AreaWindow` 解析未指定的图片搜索区域
- **THEN** 结果为该窗口自身的 `Rect`

#### Scenario: 区域窗口偏移显式搜索区域

- **WHEN** `AreaWindow` 解析窗口内显式图片搜索区域
- **THEN** 结果左上角按窗口原点偏移，宽度和高度保持不变
