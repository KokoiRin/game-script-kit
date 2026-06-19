## ADDED Requirements

### Requirement: 批量图片定位支持命中即停
系统 SHALL 允许批量图片定位按输入模板顺序命中即停。启用命中即停时，真实桌面 adapter 在找到第一张满足阈值的模板后 MUST 停止匹配后续模板，并在返回结果中把后续模板标记为 skipped。

#### Scenario: 第一个模板命中后停止
- **WHEN** 调用方按 `主页.png`、`人物.png`、`技能.png` 的顺序请求批量定位并启用命中即停
- **AND** `主页.png` 已满足最低置信度
- **THEN** desktop adapter 返回 `主页.png` 的命中结果
- **AND** `人物.png` 与 `技能.png` 的结果标记为 skipped

#### Scenario: 未命中时继续检查全部模板
- **WHEN** 调用方请求批量定位并启用命中即停
- **AND** 当前模板未满足最低置信度
- **THEN** desktop adapter 继续匹配后续模板直到命中或耗尽全部模板

#### Scenario: 日志记录 skipped 数量
- **WHEN** 批量定位启用命中即停并跳过了后续模板
- **THEN** 日志记录本轮模板总数、实际匹配数量和 skipped 数量
