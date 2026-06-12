# screen-color-sampling Specification

## Purpose
TBD - created by archiving change add-coordinate-recorder-color-sampling. Update Purpose after archive.
## Requirements
### Requirement: RGB 颜色使用领域模型表达
系统 SHALL 在领域层提供平台无关的 RGB 颜色模型，用于表达单个屏幕点的颜色。

#### Scenario: 创建 RGB 颜色
- **WHEN** 调用方使用红、绿、蓝三个通道创建颜色
- **THEN** 系统会保留每个通道的整数值

#### Scenario: 非法颜色通道被拒绝
- **WHEN** 调用方使用小于 0 或大于 255 的通道值创建颜色
- **THEN** 系统会拒绝该颜色并报告通道值必须在 0 到 255 之间

### Requirement: 业务逻辑通过颜色读取端口取色
系统 SHALL 在 `engine.ports` 中提供 `PixelColorReader` 端口，用于读取指定屏幕坐标点的 RGB 颜色。

#### Scenario: 读取指定点颜色
- **WHEN** 业务逻辑请求读取某个 `Point` 的颜色
- **THEN** 当前颜色读取 adapter 会通过 `PixelColorReader.read_color(point)` 接收该屏幕坐标并返回 `Color`

#### Scenario: 取色端口不依赖平台库
- **WHEN** 领域层、业务工具或测试代码引用颜色读取能力
- **THEN** 它们依赖 `PixelColorReader` 端口，而不是直接导入 `pyautogui` 或其他平台库

### Requirement: 桌面 adapter 实现单点取色
系统 SHALL 提供基于桌面自动化后端的单点取色 adapter，实现 `PixelColorReader` 端口。

#### Scenario: adapter 返回指定点 RGB
- **WHEN** adapter 成功读取指定屏幕坐标点的像素
- **THEN** adapter 会返回该像素前三个 RGB 通道组成的 `Color`

#### Scenario: adapter 报告取色 setup 问题
- **WHEN** adapter 因为缺少依赖、截图权限或运行环境限制无法读取屏幕像素
- **THEN** adapter 会抛出清晰的 setup 错误，并提示用户检查依赖或权限

#### Scenario: adapter 延迟加载平台依赖
- **WHEN** 只导入业务层、领域层或测试模块
- **THEN** 系统不会因为尚未初始化真实桌面取色 adapter 而立即导入或要求平台自动化依赖

### Requirement: 脚本运行时复用颜色读取端口
系统 SHALL 允许脚本运行时通过现有 `PixelColorReader` 端口读取屏幕颜色以评估条件。该能力 MUST 保持为独立屏幕读取端口，不得并入 `InputDevice`。

#### Scenario: runner 通过取色端口读取条件点颜色
- **WHEN** runner 需要评估单点颜色条件
- **THEN** 它会调用 `PixelColorReader.read_color(point)` 获取该点颜色

#### Scenario: 输入设备端口不承担取色职责
- **WHEN** 系统新增条件分支脚本能力
- **THEN** `InputDevice` 仍然只提供点击、拖拽和等待能力，不提供读取颜色方法
