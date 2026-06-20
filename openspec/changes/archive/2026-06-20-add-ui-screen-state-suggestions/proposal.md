## Why

本地 UI 已经支持输入 dry-run 模拟状态，但用户必须手写状态名。随着梦幻西游等游戏状态配置增多，手写状态容易拼错，也会让状态驱动脚本调试不够顺手。

## What Changes

- 本地控制 application 增加读取当前可用界面状态名称的用例。
- HTTP UI 增加状态名称列表接口。
- 前端为“模拟状态”输入提供配置状态候选，默认仍允许自由输入。
- 缺少状态配置时继续返回空列表，不阻止脚本运行。

## Capabilities

### New Capabilities

### Modified Capabilities
- `local-control-ui`: UI 能从状态配置读取状态名，并作为 dry-run 模拟状态输入候选。

## Impact

- 影响本地控制 application、HTTP adapter 和 UI 静态资源。
- 不改变 `ScreenStateIs` 条件、状态探测语义或配置文件格式。
- 不新增运行时依赖。
