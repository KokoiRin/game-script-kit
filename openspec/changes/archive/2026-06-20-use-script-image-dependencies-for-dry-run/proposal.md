## Why

CLI 已经可以通过 `--dry-run-image` 调试图片条件和图片目标脚本，但本地 UI 运行脚本时还不能提供 dry-run 图片命中模板。这样用户在 UI 中调试图片驱动脚本时容易误以为脚本失败，而不是缺少模拟图片输入。

## What Changes

- 脚本详情结果新增结构化图片依赖列表，独立于可读依赖文案。
- 本地 UI 的脚本详情接口返回该结构化图片依赖列表。
- 本地 UI 在 dry-run 运行脚本时，把当前脚本的图片依赖作为 dry-run 命中模板传给 application 层。
- 真实运行不使用该 dry-run 图片列表，继续读取真实屏幕。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `local-control-ui`: UI dry-run 运行脚本时可使用选中脚本的图片依赖作为模拟命中模板。

## Impact

- 影响 `portable.application.script_details` 的脚本详情结果模型。
- 影响 `LocalControlApplication.run_named_script` / `start_named_script` 的 dry-run 图片参数。
- 影响本地 UI HTTP payload 和前端运行请求。
- 需要补充 application、HTTP adapter、静态 UI 测试。
