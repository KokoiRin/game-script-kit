## Context

状态探测结果已经包含候选状态、命中状态、最佳置信度和最佳位置。真实机器上出现过 `probe-state` 返回 `未知` 且所有候选 `best_confidence=0.0` 的情况，同时截图诊断命令返回疑似全黑截图警告。普通状态探测目前不输出任何提示，用户需要额外知道要运行诊断命令或检查 macOS Screen Recording 权限。

## Goals / Non-Goals

**Goals:**

- 在状态探测结果中提供结构化诊断提示，供 CLI 和 UI 复用。
- 当探测结果高度像“截图不可用”时，提示用户检查屏幕录制权限、前台窗口或桌面会话。
- 保持状态选择和图片匹配算法不变。

**Non-Goals:**

- 不直接检测 macOS 权限状态。
- 不改变 `capture-screen`、`capture-probe-diagnostics` 的截图健康检查。
- 不把所有未命中都归因于权限问题。

## Decisions

- 在 `ScreenStateProbeResult` 上增加 `hints` 派生属性，而不是在 CLI 或 UI 入口层重复判断。这样诊断语义仍属于状态探测结果。
- 触发规则为：当前状态未知、存在至少一个已执行候选、已执行候选都有 `best_confidence`，并且最大 `best_confidence` 为 `0`。该规则和真实黑屏案例一致，同时不会覆盖普通低置信度素材偏差。
- CLI 文本模式新增“提示”分组；JSON 模式新增 `hints` 数组。
- UI 后台探测状态新增 `hints` 字段，页面在状态 tab 中展示。后台日志继续保留原有逐轮日志，不把提示写入脚本日志。

## Risks / Trade-offs

- [Risk] 某些真实画面也可能让 OpenCV 最佳置信度为 0。→ 文案使用“可能”，提示排查方向，不把它作为错误。
- [Risk] 单图定位路径目前未必提供 `best_confidence`。→ 只有所有已执行候选都提供 `best_confidence` 时才触发提示，避免根据缺失诊断信息猜测。
