## Why

命令行已经支持导出状态区域裁剪图和探测候选裁剪图，但本地 UI 只能生成诊断截图。用户调试状态识别时需要在 UI 和命令行之间切换，降低了脚本编写和素材校准效率。

## What Changes

- 本地 UI 增加“区域裁剪”和“候选裁剪”按钮。
- HTTP adapter 增加对应接口，委托 application 层已有裁剪导出用例。
- UI 展示裁剪导出的退出码、stdout 和 stderr；本轮不展示多张裁剪图片。

## Capabilities

### New Capabilities

### Modified Capabilities

- `local-control-ui`: 增加从 UI 触发状态识别裁剪导出的能力。

## Impact

- 影响本地 UI HTML/JS、HTTP adapter 和 UI 测试。
- 不改变裁剪导出 application 语义、输出目录、CLI 参数或图像匹配逻辑。
