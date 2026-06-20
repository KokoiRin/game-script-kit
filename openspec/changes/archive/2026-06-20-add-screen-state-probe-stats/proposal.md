## Why

界面状态探测现在主要靠日志观察结果，用户难以稳定判断探测是否足够快、哪些状态经常命中，以及脚本复用的后台状态是否可靠。补充结构化统计后，UI 和后续脚本编排可以直接消费探测质量信息，而不是解析日志文本。

## What Changes

- 后台界面状态探测会维护会话级统计，包括已完成轮数、最近一轮耗时、候选命中次数和候选跳过次数。
- 探测状态查询 API 返回这些统计字段，前端界面探测 tab 展示可读摘要。
- 统计只描述已完成探测轮次，不改变图片匹配、候选早停、当前状态判定或脚本执行语义。

## Capabilities

### New Capabilities

### Modified Capabilities
- `screen-state-probe`: 界面状态探测结果需要能累计会话级统计，供调用方判断探测质量。
- `local-control-ui`: 本地 UI 的后台探测状态接口和页面需要展示结构化探测统计。

## Impact

- 影响 application 层后台探测会话状态、HTTP payload 和前端渲染。
- 增加对应 application/UI 行为测试。
- 不新增第三方依赖，不改变真实桌面 adapter。
