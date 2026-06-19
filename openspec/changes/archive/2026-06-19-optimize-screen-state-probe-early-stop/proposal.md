## Why

实际 UI 日志显示，4 个场景的一轮界面探测平均约 2.1 秒，其中 OpenCV 模板匹配约占 79%。未来候选场景会扩展到几十个，如果每轮无条件匹配所有候选，刷新会明显变慢。

## What Changes

- 批量图片定位支持按输入顺序命中即停：找到满足阈值的模板后，本轮不再匹配后续模板。
- 界面状态探测把候选顺序作为优先级顺序，默认使用命中即停，未执行的后续候选在结果中标记为 skipped。
- 保留没有命中时继续检查全部候选的行为。

## Capabilities

### New Capabilities
- 无

### Modified Capabilities
- `screen-image-matching`: 批量图片定位支持命中即停，并能表达未执行的模板结果。
- `screen-state-probe`: 界面状态探测使用候选优先级早停。

## Impact

- 更新图片批量匹配结果模型，支持 skipped 状态。
- 更新 batch locator port 和 desktop adapter，新增 `stop_on_first_match` 参数。
- 更新界面状态探测 engine 的候选遍历语义。
- 增加测试覆盖早停、skipped 结果和日志内容。
