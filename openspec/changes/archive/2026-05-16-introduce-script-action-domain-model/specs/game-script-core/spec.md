## ADDED Requirements

### Requirement: Core runner 执行脚本动作模型

核心层 SHALL 提供脚本 runner，用于将脚本中的动作按顺序转换为输入设备操作。

#### Scenario: runner 按顺序执行脚本动作

- **WHEN** runner 执行包含点击、拖拽和等待动作的脚本
- **THEN** 它会按照脚本中的动作顺序发起对应操作

#### Scenario: runner 通过输入设备端口执行点击

- **WHEN** runner 执行点击动作
- **THEN** 它会先根据脚本窗口解析点击点，再通过输入设备端口发起不带鼠标按键参数的点击

#### Scenario: runner 通过输入设备端口执行拖拽

- **WHEN** runner 执行拖拽动作
- **THEN** 它会先根据脚本窗口解析起点和终点，再通过输入设备端口发起不带鼠标按键参数的拖拽

#### Scenario: runner 执行等待动作

- **WHEN** runner 执行等待动作
- **THEN** 它会等待动作指定的持续时间，并继续执行后续动作

#### Scenario: runner 不执行独立移动动作

- **WHEN** runner 执行第一版脚本动作模型
- **THEN** 它不会把独立移动指针作为脚本动作处理

#### Scenario: runner 使用脚本级窗口

- **WHEN** runner 执行绑定指定区域窗口的脚本
- **THEN** 脚本内所有点击和拖拽动作都会使用该脚本窗口解析坐标

### Requirement: Demo workflow 基于脚本模型表达

系统 SHALL 允许现有 demo workflow 通过脚本动作模型表达固定动作序列。

#### Scenario: demo workflow 构造脚本

- **WHEN** 调用方运行 demo workflow
- **THEN** demo workflow 可以构造包含点击、拖拽或等待动作的脚本，并交由 runner 执行

#### Scenario: demo workflow 保持 adapter 无关

- **WHEN** demo workflow 通过脚本模型执行
- **THEN** 它仍然只依赖输入设备抽象，不会直接导入或初始化平台 adapter
