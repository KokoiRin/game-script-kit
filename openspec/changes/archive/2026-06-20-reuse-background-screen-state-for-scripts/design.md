# Design: 真实脚本复用后台界面探测状态

## Context

`LocalControlApplication._build_screen_state_reader()` 当前返回 `_LocalScreenStateReader`。该 reader 每次读取状态都会调用 `probe_screen_state_once()`，因此脚本状态条件和 UI 后台探测各自截图、各自匹配。

`_BackgroundScreenStateProbe.snapshot()` 已经提供 `running` 和 `current_state`。这足以作为 application 层的状态缓存来源，不需要让 engine 或领域层知道 UI 探测会话。

## Decisions

1. **复用逻辑留在 application reader。**
   engine 仍只依赖 `ScreenStateReader` port；UI 和后台会话细节留在 `LocalControlApplication` 内部。

2. **只复用正在运行的非 `未知` 状态。**
   停止后的最后状态可能过期；`未知` 代表还没有有效识别结果。两者都应回退到即时探测。

3. **复用缓存时记录日志。**
   用户需要知道脚本本次判断没有重新截图，而是读取了后台探测状态。日志写入脚本运行 stdout，和现有状态探测日志保持同一观察面。

4. **即时探测仍是兜底。**
   不要求用户必须先启动界面探测。没有可用缓存时，真实脚本保持原来的行为。

## Risks

- 后台探测的 `min_confidence` 可能和脚本条件中的 `min_confidence` 不同。第一版只复用后台探测的当前状态，不重新验证置信度；如果用户需要严格置信度，可停止后台探测让脚本走即时探测。
- 后台探测间隔较长时，缓存状态可能比即时截图稍旧。限定为正在运行的探测可以降低风险，但不完全消除。
