## Context

`assets/screen-states.json` 的状态组支持一个状态下配置多个搜索项。当前 `load_screen_state_candidates()` 会读取搜索项名称，但只把状态名写入 `ScreenStateCandidate.name`，搜索项名称在进入探测流程前就丢失了。最近候选结果因此只能显示状态名。

## Goals / Non-Goals

**Goals:**

- 让 `ScreenStateCandidate` 可携带配置搜索项名称。
- 让 application 和 HTTP payload 在最近候选结果中保留该名称。
- 让 UI 使用 `状态名 / 搜索项名` 展示候选结果。

**Non-Goals:**

- 不改变当前状态选择仍以状态名为准的规则。
- 不要求资产扫描路径必须生成单独搜索项名称。
- 不改变 `screen-states.json` 的文件格式。

## Decisions

- 在 `ScreenStateCandidate` 上新增可选字段 `search_name`。
  - 理由：搜索项名称属于候选身份的一部分，应该跟随候选进入 engine 和 application，而不是在 UI 侧反查配置。
  - 备选：在 application 层根据状态名和图片路径回查配置。该方式会让 application 保存额外映射，也会在候选排序和重复图片时变脆。

- `name` 字段继续表示状态名。
  - 理由：`ScreenStateProbeResult.current_state`、脚本条件 `ScreenStateIs` 和统计计数都依赖状态名，不应被搜索项名污染。

- HTTP payload 增加 `search_name` 字段，缺失时为 `null`。
  - 理由：前端可以稳定判断是否展示搜索项名，同时兼容 assets 扫描候选。

## Risks / Trade-offs

- 领域模型字段变多 → 通过默认值保持现有构造调用兼容，并补模型校验测试。
- UI 文本可能变长 → 只在存在搜索项名时拼接 `状态 / 搜索项`，避免无配置路径产生重复信息。
