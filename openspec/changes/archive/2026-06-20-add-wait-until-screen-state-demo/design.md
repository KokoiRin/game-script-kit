## Context

`WaitUntil` 已支持任意条件，`ScreenStateIs` 已通过 `ScreenStateReader` 端口接入 runner。`script_details` 也已经能把 `WaitUntil ScreenStateIs(...)` 展示为可读步骤。因此新增示例脚本不需要改引擎，只需要新增脚本定义并注册到默认 catalog。

## Goals / Non-Goals

**Goals:**

- 提供一个最小状态等待脚本，让用户可以在 UI 和 CLI 中看到“等待主页再继续”的写法。
- 脚本应支持 dry-run 通过 `--dry-run-screen-state 主页` 直接验证成功路径。
- 脚本详情应展示状态依赖和运行前检查。

**Non-Goals:**

- 不新增新的 DSL 语义。
- 不自动根据 `assets/screen-states.json` 生成脚本。
- 不点击梦幻西游真实任务按钮；示例点击只用于说明等待后继续执行。

## Decisions

- 脚本名使用 `wait-until-screen-state-demo`，和已有 `wait-until-color-demo`、`wait-until-image-demo` 保持命名一致。
- 等待条件使用 `ScreenStateIs("主页")`，因为当前项目 assets 已配置该状态，也是已有状态分支 demo 使用的状态名。
- 等待成功后执行 `Click(Point(100, 200))`，保持示例动作和现有条件 demo 一致，避免引入真实游戏副作用。

## Risks / Trade-offs

- 如果项目没有配置 `主页` 状态，真实运行前检查会提示状态无法确认；这是示例脚本应展示的依赖检查行为，不作为错误隐藏。
