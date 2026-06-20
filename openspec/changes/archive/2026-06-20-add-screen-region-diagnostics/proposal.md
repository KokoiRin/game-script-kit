## Why

状态识别依赖 `assets/screen-states.json` 中的区域配置，但当前 UI 只能展示匹配日志，无法直观看到配置区域是否真的覆盖了游戏画面。用户在梦幻西游等真实游戏窗口上调试时，需要一个低成本方式确认区域坐标是否正确。

## What Changes

- 在本地控制 UI 中新增区域诊断能力：基于当前截图生成一张带区域框和区域名称的诊断图。
- 诊断图使用现有 `assets/screen-states.json` 中的命名区域，不改变状态识别、图片匹配或点击语义。
- UI 提供触发入口，并复用现有诊断截图预览区域展示结果。
- 如果没有状态配置或配置非法，返回清晰错误，不执行状态探测循环。

## Capabilities

### New Capabilities

### Modified Capabilities
- `local-control-ui`: 本地控制 UI 支持生成并展示状态识别区域诊断截图。

## Impact

- 影响本地控制 UI 静态页面、HTTP adapter 和 application 层本地控制用例。
- 需要在 application 层复用现有截图能力和状态配置解析结果，并在项目调试目录中保存诊断图片。
- 不新增运行时第三方依赖；优先复用现有 Pillow/截图工具链。
