## Why

目前用户只能通过代码里的内置脚本来扩展自动化流程。要让 Star 更适合长期编写游戏脚本，需要先打通“用户在项目目录新增脚本配置文件，然后 CLI/UI 直接识别并运行”的最小闭环。

## What Changes

- 新增项目脚本目录，支持从用户可编辑的 JSON 脚本文件加载脚本。
- 文件脚本可以复用已有点位别名、图片别名、搜索别名、命名区域和界面状态。
- `star list`、`star details <name>`、`star run <name>` 能识别文件脚本。
- 本地 UI 的脚本列表、脚本详情和运行入口能识别文件脚本。
- 不引入自然语言编译器、不新增 UI 内编辑器、不改变现有 Python 内置脚本语义。

## Capabilities

### New Capabilities

### Modified Capabilities
- `script-management`: 脚本管理支持从项目脚本目录加载用户可编辑配置文件脚本，并让 CLI list/details/run 使用这些脚本。
- `local-control-ui`: 本地 UI 的脚本列表、详情和运行入口支持文件脚本。

## Impact

- 影响脚本 catalog 组装、配置脚本解析、CLI list/details/run、本地 UI application 装配和相关测试。
- 新增项目脚本目录常量和 JSON 配置解析，不新增第三方依赖。
