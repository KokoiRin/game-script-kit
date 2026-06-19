## Context

前几轮已经完成点位别名、图片别名、匹配查询和 anchor。offset 是这些基础点位上的最后一层坐标计算，应该保持简单、可组合、可测试。

## Goals / Non-Goals

**Goals:**

- 固定 `Point` 可以返回偏移后的新点。
- `PointRef` 可以构造偏移点击目标。
- runner 可以解析 `OffsetTarget`，对基础点击目标结果应用偏移。
- 图片目标已有 offset 字段继续在 anchor 后应用。

**Non-Goals:**

- 不做任意数学表达式。
- 不做比例 anchor。
- 不做多目标计算。

## Decisions

### Decision 1: OffsetTarget 包装已有点击目标

offset 不需要成为新的动作，它只是点击目标的坐标派生层。runner 先解析基础目标，再应用 offset。

### Decision 2: Point.offset 返回 Point

固定点位的直接偏移是纯几何计算，返回新 `Point` 即可，不需要资源目录。

## Risks / Trade-offs

- [Risk] offset 链式嵌套可能过深。→ Mitigation：第一版只支持一层 `OffsetTarget`，辅助方法可累计到新的 offset 值。
