## ADDED Requirements

### Requirement: UI 展示界面探测统计
本地控制 UI SHALL 在界面状态探测状态中展示结构化统计。HTTP 状态查询 payload MUST 包含统计对象；页面 MUST 展示已完成轮数、最近一轮耗时、状态命中次数和候选跳过次数。没有后台探测会话时，系统 MUST 返回空统计。

#### Scenario: 查询探测状态包含统计
- **WHEN** 页面轮询 `/api/screen-state-probe`
- **THEN** HTTP 响应包含界面探测统计对象
- **AND** 统计对象包含已完成轮数和最近一轮耗时

#### Scenario: 页面展示命中频率
- **WHEN** 后台界面状态探测已经命中 `主页` 两次、`人物` 一次
- **THEN** 页面展示 `主页` 与 `人物` 的命中次数

#### Scenario: 没有探测会话时统计为空
- **WHEN** 页面在没有后台界面状态探测会话时查询状态
- **THEN** HTTP 响应中的统计对象表示 0 轮探测且没有命中或跳过计数
