## Context

图片匹配已经会输出模板、耗时、命中和置信度日志；界面状态条件目前只返回布尔值。随着脚本越来越依赖当前界面状态，状态条件也需要同等级别的可观察性。

## Goals / Non-Goals

**Goals:**
- 在 `ScreenStateIs` 条件评估处记录期望状态、实际状态、最低置信度和是否匹配。
- 让 dry-run 和真实运行都通过同一 evaluator 日志路径获得输出。
- 保持日志为可读文本，不引入新的日志后端。

**Non-Goals:**
- 不改变 `ScreenStateReader` port。
- 不改变状态探测缓存、后台探测复用或 UI 轮询行为。
- 不为颜色条件或其他条件补日志。

## Decisions

- 日志放在 condition evaluator，而不是各个 reader 实现里。reader 只负责读取当前状态，evaluator 最清楚条件期望值和最终布尔结果。
- 使用现有 `RunLogger` port。没有 logger 时保持静默，避免影响纯 engine 调用。
- 日志文本保持单行，便于 UI 日志区域扫描和测试断言。

## Risks / Trade-offs

- 日志会让 dry-run 输出多一行 → 这是本次公开行为变化，测试会同步更新。
- 后续如果引入结构化日志，当前文本可能需要迁移 → 先保持简单，避免提前设计日志系统。
