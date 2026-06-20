## Context

`star probe-state` 已经通过 application 层 `probe_screen_state_once(...)` 获取 `ScreenStateProbeResult`，CLI 只负责把结果打印出来。新增 JSON 输出应继续保持这个边界：入口层只做结果序列化，不参与图片匹配或状态判断。

## Decisions

- `--json` 是 `probe-state` 的可选输出模式，不改变默认文本输出。
- JSON 字段使用稳定英文 key，便于脚本、harness 和前端消费。
- 候选状态用枚举字符串表达：
  - `matched`: 候选命中。
  - `missed`: 候选未命中。
  - `skipped`: 候选因前序命中被提前跳过。
- `confidence` 在没有匹配结果时输出 `null`。

## Data Shape

```json
{
  "current_state": "主页",
  "known": true,
  "elapsed_ms": 7.0,
  "candidates": [
    {
      "name": "主页",
      "search_name": "主页标识",
      "status": "matched",
      "elapsed_ms": 4.0,
      "confidence": 0.91
    }
  ]
}
```

## Non-Goals

- 不新增实时 watch 模式。
- 不调整状态识别配置格式。
- 不优化图片匹配性能。
