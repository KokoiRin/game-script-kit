## ADDED Requirements

### Requirement: 脚本运行时复用颜色读取端口
系统 SHALL 允许脚本运行时通过现有 `PixelColorReader` 端口读取屏幕颜色以评估条件。该能力 MUST 保持为独立屏幕读取端口，不得并入 `InputDevice`。

#### Scenario: runner 通过取色端口读取条件点颜色
- **WHEN** runner 需要评估单点颜色条件
- **THEN** 它会调用 `PixelColorReader.read_color(point)` 获取该点颜色

#### Scenario: 输入设备端口不承担取色职责
- **WHEN** 系统新增条件分支脚本能力
- **THEN** `InputDevice` 仍然只提供点击、拖拽和等待能力，不提供读取颜色方法
