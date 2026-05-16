## ADDED Requirements

### Requirement: 业务逻辑依赖输入设备抽象

游戏自动化业务 workflow SHALL 通过输入设备抽象调用鼠标指针动作，而不是直接调用平台专用的鼠标或键盘 API。

#### Scenario: workflow 可以使用测试输入设备运行

- **WHEN** demo workflow 使用 fake 输入设备实现执行
- **THEN** workflow 会记录预期的鼠标指针操作，并且不需要 macOS 自动化 API

#### Scenario: workflow 不依赖 macOS

- **WHEN** core workflow 模块在非 macOS 或测试环境中被导入
- **THEN** 导入过程不会导入或初始化 macOS 鼠标指针 adapter

### Requirement: Demo workflow 组合可复用动作

系统 SHALL 提供一个 demo workflow，通过抽象接口组合多个鼠标指针操作，用来演示游戏脚本逻辑如何与设备行为分离。

#### Scenario: demo workflow 使用注入的设备

- **WHEN** demo workflow 被构造或调用
- **THEN** 调用方可以提供用于执行 workflow 动作的输入设备实现

#### Scenario: demo workflow 保持平台无关

- **WHEN** demo workflow 执行移动、点击和拖动行为
- **THEN** 它只通过输入设备抽象发起这些动作

### Requirement: Core workflow 无需真实鼠标移动即可测试

系统 SHALL 允许使用 fake 输入设备验证 core workflow 行为，该 fake 设备会捕获 workflow 请求的操作。

#### Scenario: 测试验证操作顺序

- **WHEN** core workflow 使用 fake 输入设备进行测试
- **THEN** 测试可以断言请求的鼠标指针操作顺序和参数
