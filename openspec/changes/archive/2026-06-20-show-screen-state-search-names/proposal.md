## Why

状态配置允许一个状态包含多个搜索项，例如同一个界面用多个按钮或标题作为识别标识。当前最近候选结果只展示状态名，多个搜索项会显示成重复状态，用户无法判断具体是哪张素材命中、未命中或被跳过。

## What Changes

- 状态配置生成探测候选时保留搜索项名称。
- 后台探测状态候选摘要和 HTTP payload 增加搜索项名称字段。
- UI 最近候选结果展示中同时显示状态名和搜索项名。
- 兼容没有配置文档、直接从 `assets/` 扫描图片生成候选的旧路径。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `screen-state-probe`: 状态探测候选可携带配置搜索项名称，并在候选摘要中保留。
- `local-control-ui`: 最近候选结果展示状态名和搜索项名。

## Impact

- 影响领域候选模型、状态配置读取、application 候选摘要、HTTP payload、UI 展示和测试。
- 不改变当前状态选择规则、候选优先级或图像匹配 adapter contract。
