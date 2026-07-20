## Why

现有 Star 依赖真实游戏窗口做端到端验证，但原目标游戏已经不再稳定使用，导致图片点击、状态等待和 Run Plan 很难持续复现。项目需要一个无外部副作用、状态可控且结果可由外部检查的本地视觉靶场，作为后续功能开发的稳定目标应用。

## What Changes

- 新增独立 `star-lab` 本地网页靶场，不复用 Star 控制 UI，也不依赖 Star 核心执行模块。
- 提供“任务处理台”场景，覆盖主页、任务列表、加载、确认和完成状态。
- 提供重置、状态读取、事件读取和页面动作 HTTP 接口，以便测试程序独立核验真实结果。
- 页面支持正常、慢加载和目标缺失模式，用来重复验证成功、等待和未满足条件路径。
- 增加一条通过真实 HTTP 页面完成任务流程的 adapter 级验证路径，并保留后续真实屏幕 smoke 的入口。

## Capabilities

### New Capabilities

- `visual-automation-lab`: 定义独立视觉靶场的启动方式、任务状态机、可视页面、故障模式和外部真值接口。

### Modified Capabilities

无。

## Impact

- 新增独立 `star_visual_lab` package、静态页面资源、`star-lab` console script 和测试。
- 更新项目 README，说明靶场用途和启动方式。
- 不修改脚本 DSL、runner、平台 adapter 或现有 `star` CLI 行为。
- 不新增第三方运行依赖。
