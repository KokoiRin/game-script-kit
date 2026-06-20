## ADDED Requirements

### Requirement: UI 使用脚本状态依赖填充 dry-run 状态
本地控制 UI SHALL 从脚本详情接口获取结构化界面状态依赖，并允许用户把当前选中脚本的第一个状态依赖填入 dry-run 模拟状态输入。HTTP adapter MUST 只转发 application 层生成的结构化状态依赖，不得通过解析展示文案推导状态依赖。

#### Scenario: 使用脚本状态依赖
- **WHEN** 用户选择包含 `ScreenStateIs("主页")` 的脚本
- **AND** 用户点击使用脚本状态按钮
- **THEN** dry-run 模拟状态输入被设置为 `主页`
- **AND** 页面展示已使用该脚本状态的提示

#### Scenario: 脚本没有状态依赖
- **WHEN** 用户选择不包含 `ScreenStateIs` 条件的脚本
- **AND** 用户点击使用脚本状态按钮
- **THEN** dry-run 模拟状态输入保持不变
- **AND** 页面展示当前脚本没有状态依赖的提示

#### Scenario: 脚本详情接口返回结构化状态依赖
- **WHEN** UI 请求包含 `ScreenStateIs("主页")` 的脚本详情
- **THEN** HTTP 响应包含结构化字段 `state_dependencies`
- **AND** `state_dependencies` 包含 `主页`
