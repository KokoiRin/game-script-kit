## Why

本地 UI 已能分别展示状态配置摘要和最近候选探测结果，但用户仍需要手动对照“配置里的搜索项”和“最近结果里的候选项”。为了让用户管理识别素材更自然，配置摘要应直接显示每个搜索项最近一次是否命中、最佳置信度和最佳位置。

## What Changes

- UI 在状态配置摘要中合并最近一轮探测候选结果。
- 每个配置搜索项展示最近状态：命中、未命中、跳过或暂无结果。
- 每个配置搜索项展示最近置信度、最佳置信度和最佳位置。
- 不修改状态配置文件格式、HTTP payload、状态探测语义或图片匹配算法。

## Capabilities

### New Capabilities

### Modified Capabilities
- `local-control-ui`: 状态配置摘要结合最近探测结果展示每个搜索项的匹配情况。

## Impact

- 影响本地 UI 静态 JS 展示逻辑和 UI 测试。
- 不影响 application、adapter、脚本运行或状态探测核心逻辑。
- 影响 `local-control-ui` OpenSpec 规格。
