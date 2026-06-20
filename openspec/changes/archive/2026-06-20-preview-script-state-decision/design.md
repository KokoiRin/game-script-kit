## Context

本地控制 UI 已经从 application 层获取 `state_decisions`，并在脚本详情中展示状态命中和未命中分支摘要。界面探测 tab 也会维护最近一次探测到的 `latestScreenState`。当前缺口是两个信息只并列存在，用户需要手动判断当前界面下脚本会走哪条分支。

## Goals / Non-Goals

**Goals:**

- 在脚本详情中基于最近探测状态展示每个状态决策的当前分支预览。
- 当界面探测状态更新时，已展示的脚本详情预览同步刷新。
- 保持 HTTP adapter 和 application 层职责不变。

**Non-Goals:**

- 不改变 `ScreenStateIs` 的运行语义。
- 不新增后端接口或 `state_decisions` payload 字段。
- 不在前端解释脚本模型，只消费 application 层已经生成的结构化摘要。

## Decisions

- 前端保存最近一次成功加载的脚本详情 payload。
  - 理由：界面探测轮询更新 `latestScreenState` 后，可以用同一份 payload 重新渲染脚本详情，避免额外请求。
  - 备选：每次探测状态变化都重新请求脚本详情。该方式会增加无必要的 HTTP 请求，且脚本结构通常不会因探测状态变化。

- 分支预览只比较 `latestScreenState` 和 `decision.state`。
  - 理由：payload 已经由 application 层归纳为状态决策摘要，前端只做展示层组合，不进入脚本语义解释。
  - 备选：前端解析步骤文案中的 `ScreenStateIs(...)`。这会破坏既有分层约束，并且依赖展示文案格式。

## Risks / Trade-offs

- 最新探测状态可能滞后于真实游戏界面 → UI 文案使用“当前预览”表达，并继续以真实脚本执行结果为准。
- 没有探测结果时预览信息有限 → 显示“当前：未知”，避免误导用户。
