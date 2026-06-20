## Why

用户调试界面状态识别时，当前需要分别运行 `capture-screen` 和 `probe-state`，再人工把截图警告、当前状态和候选诊断提示拼在一起判断问题。现在真实机器上已经出现“截图疑似全黑、状态全未命中”的情况，需要一个更直接的一键诊断入口来确认是权限、前台窗口、桌面会话还是配置/素材问题。

## What Changes

- 新增 `star diagnose-screen` CLI 子命令，用于一次性执行屏幕截图诊断和单轮界面状态探测。
- application 层提供组合用例，负责串联截图诊断与状态探测并生成用户可见摘要。
- CLI 继续保持薄入口，只传递最低置信度参数并打印 application 结果。
- 不修改图片匹配算法、状态选择规则、脚本 DSL 或 UI 行为。

## Capabilities

### New Capabilities

### Modified Capabilities
- `screen-state-probe`: 增加命令行屏幕识别环境诊断入口，复用已有截图和状态探测能力。

## Impact

- 影响 `LocalControlApplication` 的诊断用例。
- 影响 `star` CLI 子命令和相关 CLI 测试。
- 影响 `screen-state-probe` OpenSpec 规格。
- 不新增第三方依赖。
