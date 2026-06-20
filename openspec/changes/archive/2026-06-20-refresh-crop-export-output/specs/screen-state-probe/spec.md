## ADDED Requirements

### Requirement: 裁剪导出目录只保留最近一次结果

系统 SHALL 在执行状态区域裁剪导出或探测候选裁剪导出前刷新对应输出目录，使目录中的 PNG 裁剪图只代表最近一次导出结果。系统 MUST NOT 因旧 PNG 存在而让用户误判本轮导出内容。

#### Scenario: 区域裁剪导出清理旧 PNG

- **WHEN** 用户运行 `star capture-region-crops`
- **AND** 输出目录中存在上一次导出的 PNG
- **THEN** 系统在保存本轮区域裁剪图前删除旧 PNG
- **AND** 输出目录中的 PNG 只包含本轮区域裁剪结果

#### Scenario: 探测候选裁剪导出清理旧 PNG

- **WHEN** 用户运行 `star capture-probe-crops`
- **AND** 输出目录中存在上一次导出的 PNG
- **THEN** 系统在保存本轮候选裁剪图前删除旧 PNG
- **AND** 输出目录中的 PNG 只包含本轮候选裁剪结果

#### Scenario: 本轮没有候选裁剪图

- **WHEN** 用户运行 `star capture-probe-crops`
- **AND** 本轮状态探测没有任何候选包含 `best_rect`
- **THEN** 系统删除旧候选裁剪 PNG
- **AND** 输出目录中不残留上一次候选裁剪图
