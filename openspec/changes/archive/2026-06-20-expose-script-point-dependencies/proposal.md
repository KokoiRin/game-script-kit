## Why

脚本已经支持 `PointRef("头像")` 这类点位别名，但脚本详情目前只把点位混在通用依赖文本里。用户在 UI 中选择脚本时，无法像状态依赖和图片依赖一样单独看到脚本依赖了哪些点位，这会阻碍后续点位管理和脚本可读性。

## What Changes

- 脚本详情结果新增结构化 `point_dependencies` 字段。
- CLI `star details` 展示“点位依赖”分组。
- UI `/api/script-details` 返回 `point_dependencies`。
- 本地 UI 脚本详情展示点位依赖分组。
- 不改变 `PointRef` 执行语义、点位配置模型或脚本运行行为。

## Capabilities

### New Capabilities

### Modified Capabilities
- `script-management`: 脚本详情暴露结构化点位依赖并在 CLI 中展示。
- `local-control-ui`: 本地 UI 脚本详情接口和页面展示点位依赖。

## Impact

- 影响脚本依赖分析、脚本详情 presenter、CLI details 输出、本地 UI payload 和前端脚本详情展示。
- 不新增平台能力或第三方依赖。
