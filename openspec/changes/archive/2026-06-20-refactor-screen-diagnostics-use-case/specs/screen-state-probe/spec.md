## MODIFIED Requirements

### Requirement: CLI 提供界面状态截图诊断入口

系统 SHALL 提供命令行截图诊断入口，用于帮助用户调试界面状态识别素材和区域。CLI MUST 复用 application 层截图诊断用例，不得在入口层直接截图、绘制区域或解析状态配置。application 层 MAY 通过专用屏幕诊断 use case 承载截图诊断编排，但 MUST 保持 CLI 命令名、退出码、stdout 和 stderr 语义稳定。

#### Scenario: 保存当前屏幕截图

- **WHEN** 用户运行 `star capture-screen`
- **THEN** CLI 保存一张当前屏幕截图
- **AND** stdout 输出截图保存路径
- **AND** CLI 返回 application 层用例的退出码

#### Scenario: 保存状态识别区域诊断图

- **WHEN** 用户运行 `star capture-region-diagnostics`
- **THEN** CLI 保存一张带状态识别区域框的诊断截图
- **AND** stdout 输出诊断图保存路径
- **AND** CLI 返回 application 层用例的退出码

#### Scenario: 截图诊断失败

- **WHEN** 截图 adapter 不可用、截图权限缺失、状态配置非法或缺少命名区域
- **AND** 用户运行截图诊断命令
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因

### Requirement: CLI 提供界面状态命名区域裁剪导出

系统 SHALL 提供命令行区域裁剪导出入口，用于把当前屏幕中的状态识别命名区域保存为独立图片。裁剪导出 MUST 复用 application 层截图诊断用例和状态配置解析，不得在 CLI 入口层直接截图、裁剪或解析状态配置。application 层 MAY 通过专用屏幕诊断 use case 承载裁剪导出编排，但 MUST 保持 CLI 命令名、退出码、stdout 和 stderr 语义稳定。

#### Scenario: 保存命名区域裁剪图

- **WHEN** 用户运行 `star capture-region-crops`
- **AND** `assets/screen-states.json` 配置了命名区域
- **THEN** CLI 为每个命名区域保存一张裁剪图
- **AND** stdout 输出每个裁剪图保存路径
- **AND** CLI 返回 application 层用例的退出码

#### Scenario: 区域裁剪导出失败

- **WHEN** 截图 adapter 不可用、屏幕尺寸不可用、状态配置非法、缺少状态配置或缺少命名区域
- **AND** 用户运行 `star capture-region-crops`
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因

### Requirement: CLI 导出界面探测诊断截图

系统 SHALL 提供 `star capture-probe-diagnostics` 子命令，用于执行一轮界面状态探测并保存带候选最佳匹配框的诊断截图。CLI MUST 复用 application 层用例，不得在入口层执行截图、绘图或图片匹配。application 层 MAY 通过专用屏幕诊断 use case 承载探测诊断编排，但 MUST 保持 CLI 命令名、退出码、stdout 和 stderr 语义稳定。

#### Scenario: 导出探测诊断截图

- **WHEN** 用户运行 `star capture-probe-diagnostics`
- **THEN** 系统执行一轮界面状态探测
- **AND** 系统保存一张诊断截图
- **AND** 诊断截图包含候选的最佳匹配位置
- **AND** CLI 输出保存路径和当前探测状态

#### Scenario: 传递最低置信度

- **WHEN** 用户运行 `star capture-probe-diagnostics --min-confidence 0.75`
- **THEN** 系统使用 `0.75` 作为本次状态探测默认最低置信度

#### Scenario: 探测诊断截图失败

- **WHEN** 截图能力、屏幕尺寸或状态探测不可用
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因

### Requirement: CLI 导出界面探测候选裁剪图

系统 SHALL 提供 `star capture-probe-crops` 子命令，用于执行一轮界面状态探测并把每个候选的最佳匹配位置导出为独立裁剪图。CLI MUST 复用 application 层用例，不得在入口层执行截图、裁剪或图片匹配。application 层 MAY 通过专用屏幕诊断 use case 承载候选裁剪编排，但 MUST 保持 CLI 命令名、退出码、stdout 和 stderr 语义稳定。

#### Scenario: 导出候选裁剪图

- **WHEN** 用户运行 `star capture-probe-crops`
- **THEN** 系统执行一轮界面状态探测
- **AND** 系统保存每个有 `best_rect` 的候选裁剪图
- **AND** CLI 输出每个裁剪图保存路径

#### Scenario: 传递最低置信度

- **WHEN** 用户运行 `star capture-probe-crops --min-confidence 0.75`
- **THEN** 系统使用 `0.75` 作为本次状态探测默认最低置信度

#### Scenario: 没有可裁剪候选

- **WHEN** 本轮状态探测没有任何候选包含 `best_rect`
- **THEN** CLI 返回成功
- **AND** CLI 输出没有保存候选裁剪图

#### Scenario: 候选裁剪失败

- **WHEN** 截图能力、屏幕尺寸或状态探测不可用
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因
