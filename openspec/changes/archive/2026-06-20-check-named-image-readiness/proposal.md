## Why

命名图片已经能进入 UI dry-run 的 `image_dependencies`，但脚本详情里的“依赖检查”仍按展示字符串判断图片路径。结果是 `ImageRef("离开")` 这类已在脚本资源目录中注册的图片会显示为无法确认，降低用户对脚本可运行性的判断质量。

## What Changes

- 脚本详情依赖检查使用脚本 `resources` 解析命名图片。
- 已解析命名图片指向存在且后缀受支持的 assets 文件时，依赖检查显示可用。
- 已解析命名图片指向缺失或不支持文件时，依赖检查显示缺失。
- 未配置的命名图片显示为缺失，而不是被当成普通路径。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `local-control-ui`: 脚本详情依赖检查支持命名图片资源。

## Impact

- 影响 `portable.application.script_details` 的 readiness 生成逻辑。
- 不改变 UI payload 结构、前端渲染、runner 或图像匹配 adapter。
- 需要补充命名图片 readiness 的 application 测试。
