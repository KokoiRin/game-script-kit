# Change: add-cli-screen-state-probe

## Why

用户写状态驱动脚本前，需要先确认当前桌面上的游戏界面能被识别成哪个状态。现在这个能力主要在 UI 的界面探测 tab 里，命令行用户没有轻量的一次性验证入口。

## What Changes

- 增加 `star probe-state` 子命令，执行一轮界面状态探测。
- 输出当前状态、候选项命中情况、耗时和置信度。
- 复用本地 desktop composition 和 application 层状态探测用例。

## Impact

- Affected specs: `screen-state-probe`
- Affected code: CLI entrypoint, CLI tests
