# Design: 使用探测状态填充 dry-run 模拟状态

## Context

当前 UI 已有两条链路：

- 脚本控制区通过 `dry-run-screen-state` 输入把模拟状态传给 `/api/run-script`。
- 界面探测区通过 `/api/screen-state-probe` 获取 `current_state` 并渲染到页面。

缺口是前端没有把这两个 UI 状态连接起来。后端 application 和 HTTP adapter 已经提供所需信息，因此本 change 不需要新增 application 用例。

## Decisions

1. **只在用户点击按钮时填充。**
   自动同步可能覆盖用户正在手动构造的测试状态。显式按钮更符合 dry-run 的“我想模拟这个状态”语义。

2. **前端缓存最近一次探测状态。**
   `renderScreenStateStatus` 已经是所有探测状态渲染的汇聚点，在这里维护 `latestScreenState` 可以避免重复解析 UI 文案。

3. **`未知` 不覆盖现有输入。**
   `未知` 是默认兜底值，不代表真实识别到了一个可用界面。点击按钮时如果没有可用状态，只更新状态提示，不清空或覆盖输入。

4. **不新增后端接口。**
   现有 `/api/screen-state-probe` 已经返回 `current_state`，前端轮询和按钮都可以使用这份状态。

## Risks

- 用户可能在探测停止后点击按钮，使用的是最后一次识别到的状态。页面文案应表达为“使用探测状态”，不是“实时状态”。
- 如果状态刚好识别为 `未知`，按钮不会写入输入框，避免误导用户以为这是有效状态。
