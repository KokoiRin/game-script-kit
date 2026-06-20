## Why

界面状态识别开始支持多个候选和早停后，用户需要知道最近一轮每个候选的命中、跳过、耗时和置信度，才能调试区域、素材和候选顺序。当前 UI 只有总统计和日志，定位配置问题时还需要读长日志。

## What Changes

- 界面状态探测状态 payload 增加最近一轮候选结果列表。
- UI 在界面探测 tab 中展示最近一轮候选结果，包括状态名、命中状态、耗时和置信度。
- 没有探测会话或还没有完成探测轮次时，候选结果为空并展示清晰提示。
- 不改变界面状态识别算法、早停规则或脚本执行语义。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `local-control-ui`: 界面探测状态接口和页面展示最近一轮候选结果。
- `screen-state-probe`: 后台循环探测会话快照保留最近一轮候选结果，供 UI 消费。

## Impact

- 影响 application 层后台界面探测状态模型、HTTP payload 转换、UI 静态页面和相关测试。
- 不新增平台依赖，不改变图像匹配 port contract。
