## Context

项目已经有两个分散能力：`capture-screen` 可以保存当前屏幕并提示疑似全黑截图，`probe-state` 可以执行一轮状态探测并返回当前状态、候选结果和诊断提示。用户排查 UI 识别不到图片时，需要把两条命令的输出合并理解，反馈链路偏长。

本变更只增加一个组合用例，帮助用户快速确认“Star 是否看得到屏幕、状态探测是否有有效候选”。它必须遵守 ports-and-adapters 边界：CLI 不直接截图、不直接匹配图片、不解释候选置信度。

## Goals / Non-Goals

**Goals:**

- 提供 `star diagnose-screen`，一次输出截图路径、截图警告、当前识别状态和状态探测提示。
- 在 application 层组合已有截图诊断和状态探测能力。
- 保持现有 `capture-screen`、`probe-state`、UI 和脚本执行语义不变。

**Non-Goals:**

- 不优化图片匹配速度。
- 不修改状态识别配置格式。
- 不新增 UI 按钮或 HTTP endpoint。
- 不自动修复 macOS 权限或前台窗口问题。

## Decisions

1. **在 `LocalControlApplication` 增加组合用例。**
   - 理由：截图和状态探测都属于本地控制应用层用户意图，组合逻辑放在 application 层可以让 CLI 继续只做输入输出转换。
   - 备选：在 CLI 中依次调用 `capture_screen_screenshot()` 和 `probe_screen_state_once()`。这会让 CLI 承担用例编排，也更容易在入口层复制错误处理。

2. **复用 `ControlResult` 作为诊断命令输出。**
   - 理由：CLI 已经有 `_print_control_result`，截图类命令也都用 stdout/stderr/exit_code 表达用户可见结果。诊断命令不需要新增结构化 API。
   - 备选：新增专用 dataclass。当前没有 UI/JSON 需求，专用结构会增加转换层而收益有限。

3. **截图疑似全黑只作为警告，不阻断状态探测。**
   - 理由：保存到的截图仍然有诊断价值，状态探测也能进一步产生“全部最佳置信度为 0”的提示。
   - 备选：截图全黑直接返回失败。这样会丢失状态探测侧的候选和配置反馈。

4. **截图失败时停止；状态探测配置错误返回配置错误。**
   - 理由：截图失败说明无法形成本轮环境诊断的基础信息；状态配置错误属于用户可修复配置问题，应返回与 `probe-state` 一致的分类。

## Risks / Trade-offs

- [Risk] 命令输出会比单独 `probe-state` 更长。→ Mitigation：保持摘要格式，只输出截图路径、当前状态、耗时、提示和候选摘要。
- [Risk] 用户可能把诊断命令当作性能测试。→ Mitigation：规格明确这是环境诊断入口，不改变或优化匹配算法。
