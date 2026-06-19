## ADDED Requirements

### Requirement: 界面状态探测优先使用批量图片定位
系统 SHALL 在界面状态探测中优先使用批量图片定位能力。已装配批量定位 adapter 时，一轮界面状态探测 MUST 只请求一次批量定位；未装配批量定位 adapter 时，系统 MAY 回退到逐个单图定位。

#### Scenario: 使用批量定位探测界面
- **WHEN** application 层已装配批量图片定位 adapter 且用户启动界面状态探测
- **THEN** 每轮界面状态探测通过一次批量定位请求匹配所有候选图片

#### Scenario: 回退到单图定位
- **WHEN** 界面状态探测未装配批量图片定位 adapter 但已装配单图定位 adapter
- **THEN** 系统继续逐个匹配候选图片并返回同样形状的探测结果
