## Why

真实用户脚本更倾向写 `ImageRef("离开")` 这种命名图片，而不是在每个脚本步骤中重复完整路径。当前 UI dry-run 只会自动使用直接 `ImageTemplate` 图片依赖，导致已经资源化的命名图片脚本无法在 UI 模拟运行中自动命中。

## What Changes

- 脚本详情的结构化图片依赖会解析 `ImageRef` 到脚本 `resources` 中注册的 `ImageTemplate` 路径。
- UI dry-run 自动提交图片依赖时，命名图片脚本也能获得 dry-run 图片命中模板。
- 未知命名图片依赖继续由现有运行/依赖检查路径报告，不在脚本详情阶段吞掉错误。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `local-control-ui`: UI dry-run 使用脚本图片依赖时支持从脚本资源目录解析命名图片。

## Impact

- 影响 `portable.application.script_details` 的图片依赖收集逻辑。
- 不改变 runner、真实图像匹配 adapter 或前端请求格式。
- 需要补充命名图片脚本详情和 UI dry-run 相关测试。
