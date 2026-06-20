## Why

`LocalControlApplication` 同时承载脚本运行、后台会话、界面状态探测、屏幕诊断编排和 Pillow 图片产物处理。屏幕诊断相关职责已经形成独立用例：截图、区域诊断、探测诊断、区域裁剪和候选裁剪。继续留在本地控制 facade 中会降低局部性，也让后续优化诊断产物时更容易误触脚本运行和 HTTP/UI 行为。

## What Changes

- 新增 application 层 `ScreenDiagnosticsUseCase`，承载现有 6 个屏幕诊断用例。
- 新增诊断产物 helper，收拢 Pillow 绘图、裁剪、黑屏检测、旧 PNG 清理和安全文件名处理。
- `LocalControlApplication` 保留现有公开方法名和返回结果，但内部委托给诊断 use case。
- CLI、HTTP endpoint 和前端 payload 语义保持不变。

## Capabilities

### Modified Capabilities

- `screen-state-probe`: CLI 屏幕诊断入口继续复用 application 层用例，内部职责从本地控制 facade 下沉到专用诊断 use case。
- `local-control-ui`: UI 诊断入口继续调用本地控制 application facade，HTTP 和前端语义不变。

## Impact

- 影响文件集中在 portable application 层和相关测试。
- 不新增 CLI 子命令、不修改 HTTP endpoint、不改变用户可见输出格式。
