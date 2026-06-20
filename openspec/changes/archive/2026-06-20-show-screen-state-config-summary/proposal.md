## Why

界面状态识别已经支持 `assets/screen-states.json`，但 UI 只能启动探测和看日志，用户无法直接确认当前配置了哪些状态、图片、区域和阈值。展示配置摘要可以让“搜索任务”从脚本里分离出来并可检查，降低编写状态驱动脚本前的排错成本。

## What Changes

- application 层提供界面状态配置摘要，包含状态、搜索项、图片文件、区域和最低置信度。
- HTTP UI 增加读取配置摘要的接口。
- 界面探测 tab 展示当前状态配置清单；没有配置或配置非法时展示清晰状态，不影响手动探测按钮。
- 不提供配置编辑、图片裁剪或自动生成配置功能。

## Capabilities

### New Capabilities

### Modified Capabilities
- `screen-state-probe`: 状态配置需要可被 application 层读取为用户可理解的摘要。
- `local-control-ui`: 本地 UI 需要展示界面状态配置摘要。

## Impact

- 影响 `screen_state_config`、`LocalControlApplication`、本地 HTTP adapter 和前端静态资源。
- 增加 application、HTTP 和 UI 静态行为测试。
- 不新增外部依赖，不改变状态探测匹配语义。
