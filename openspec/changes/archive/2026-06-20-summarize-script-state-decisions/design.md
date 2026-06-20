## Context

`ScriptDetailsResult` 已经包含步骤摘要、依赖、结构化状态依赖和 readiness。状态决策摘要属于同一类只读 presenter 信息，应放在脚本详情生成边界，而不是 UI 直接解释脚本模型。

## Goals / Non-Goals

**Goals:**
- 收集脚本中所有 `If(ScreenStateIs(...))` 决策。
- 复用现有步骤摘要生成逻辑，展示 then/else 分支会执行的内容。
- 通过 HTTP payload 给前端结构化字段。

**Non-Goals:**
- 不分析非状态条件。
- 不做控制流可视化图或执行路径模拟。
- 不改变现有 `state_dependencies` 和 readiness 字段。

## Decisions

- 状态决策摘要放在 `script_details`，因为它描述“脚本如何被展示给用户”，而不是运行依赖检查。
- 摘要只覆盖 `If` 的 `ScreenStateIs` 条件。`WaitUntil(ScreenStateIs)` 是等待语义，不是分支决策，暂不纳入。
- then/else 使用已有步骤摘要文本，避免引入第二套动作描述规则。

## Risks / Trade-offs

- 嵌套状态分支可能产生多条摘要 → 按脚本阅读顺序输出，保持简单可预期。
- else 分支为空时可能看起来缺信息 → 用空列表表示没有动作，前端展示为“无”。
