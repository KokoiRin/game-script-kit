## Context

`star probe-state` 已经提供单次状态探测，`star run --dry-run-screen-state` 已经可以用固定状态验证 `ScreenStateIs` 分支。新增能力只把这两步串起来：CLI 调用 application 层探测一次，拿到 `current_state` 后仍然走现有 dry-run 固定状态路径。

## Decisions

- 新参数命名为 `--dry-run-probed-screen-state`，语义明确绑定 dry-run。
- 如果用户未提供 `--dry-run`，CLI 返回配置错误，不运行脚本。
- 如果用户同时显式提供 `--dry-run-screen-state` 和 `--dry-run-probed-screen-state`，CLI 返回配置错误，避免状态来源歧义。
- 探测失败时不运行脚本，并沿用 `probe-state` 的配置错误和运行错误分类。
- 探测结果为 `未知` 时仍然运行 dry-run，因为这是一次有效探测结果，脚本分支应按未知状态自然评估。

## Non-Goals

- 不新增持续 watch 或自动循环运行。
- 不把真实状态 reader 注入 dry-run runner。
- 不改变 UI 的“使用探测状态”按钮行为。
