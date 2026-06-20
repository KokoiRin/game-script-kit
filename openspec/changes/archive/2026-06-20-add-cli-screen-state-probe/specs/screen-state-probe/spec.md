## ADDED Requirements

### Requirement: CLI 支持单次界面状态探测
系统 SHALL 提供 `star probe-state` 子命令，用于执行一轮界面状态探测并输出当前状态和候选结果。CLI MUST 复用 application 层状态探测用例，不得在入口层执行图片匹配或解释状态识别规则。

#### Scenario: 探测并输出当前状态
- **WHEN** 用户运行 `star probe-state`
- **THEN** CLI 执行一轮状态探测
- **AND** 输出当前状态、总耗时和候选项结果

#### Scenario: 指定最低置信度
- **WHEN** 用户运行 `star probe-state --min-confidence 0.75`
- **THEN** CLI 使用 `0.75` 作为本次状态探测最低置信度

#### Scenario: 配置错误
- **WHEN** 状态配置非法
- **AND** 用户运行 `star probe-state`
- **THEN** CLI 返回配置错误并把原因写入 stderr

#### Scenario: 探测运行失败
- **WHEN** 图像定位 adapter 不可用
- **AND** 用户运行 `star probe-state`
- **THEN** CLI 返回运行错误并把原因写入 stderr
