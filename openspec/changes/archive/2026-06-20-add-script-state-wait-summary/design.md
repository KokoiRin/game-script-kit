## Context

`describe_script_details` 已负责把脚本步骤转换成 CLI/UI 共用的只读摘要，并收集状态依赖、图片依赖和 `If(ScreenStateIs(...))` 状态决策。`WaitUntil(ScreenStateIs(...))` 当前只出现在 `steps` 文本里，没有结构化摘要，因此 UI 无法像状态决策一样根据当前探测状态展示“等待已满足/未满足”。

## Goals / Non-Goals

**Goals:**

- 在 application 层脚本详情结果中增加状态等待摘要，保持 CLI 和 UI 入口薄。
- 递归收集脚本中的 `WaitUntil(ScreenStateIs(...))`，包含嵌套在 `Repeat`、`If` 分支中的等待。
- CLI 和 UI 都展示状态等待分组；UI 使用已有 `latestScreenState` 给出当前等待是否满足。

**Non-Goals:**

- 不改变 `WaitUntil` 或 `ScreenStateIs` 的执行语义。
- 不把等待摘要用于自动运行决策。
- 不新增状态探测配置或自然语言脚本能力。

## Decisions

- 在 `ScriptDetailsResult` 中新增 `state_waits: tuple[str, ...]`。它和 `state_dependencies` 不同，前者表达“这些状态用于等待”，后者表达“脚本依赖这些状态配置”。
- 在 `script_details.py` 内递归收集等待摘要，保持脚本语义解释集中在 application presenter seam；CLI 和 HTTP/UI 只消费结果。
- UI 复用现有 `latestScreenState`，展示 `当前：已满足`、`当前：未满足` 或 `当前：未知`。这样不需要 UI 触发额外探测，也不影响脚本运行。
- CLI 新增“状态等待”分组，用稳定文本展示每个等待状态，方便终端用户检查脚本意图。

## Risks / Trade-offs

- [Risk] `state_dependencies` 和 `state_waits` 都会出现同一个状态，用户可能觉得重复。→ 用不同分组名表达不同语义：一个是外部依赖，一个是脚本控制流用途。
- [Risk] 未来如果 `WaitUntil` 支持更复杂的组合条件，当前结构只覆盖 `ScreenStateIs`。→ 本轮只针对已有条件模型，后续组合条件出现时再扩展收集器。
