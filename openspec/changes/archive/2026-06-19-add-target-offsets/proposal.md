## Why

固定点位和图片 anchor 能表达基础位置，但游戏操作经常需要“在某个点右边/下方一点”。本轮新增通用点位偏移，让脚本可以从固定点位、点位别名或图片 anchor 派生最终点击点。

## What Changes

- 新增 `Point.offset(x=..., y=...)`，返回偏移后的新点位。
- 新增 `OffsetTarget`，允许 `Click` 对固定点、点位别名或图片目标应用偏移。
- 新增 `PointRef.offset(...)` 脚本辅助方法。
- 明确 `ImageTarget.offset` 在 anchor 点位之后应用。
- 不做任意公式、比例点或跨多个目标计算。

## Capabilities

### New Capabilities

- `target-offsets`: 覆盖固定点位、命名点位和图片目标的偏移点击语义。

### Modified Capabilities

- `script-action-model`: `Click` 新增偏移目标作为合法点击目标。
- `game-script-core`: runner 解析偏移目标并在基础点位后应用 offset。

## Impact

- 影响 `domain.geometry`、点击目标模型和 runner 目标解析。
- 增加领域模型和 runner 测试。
- 不新增平台依赖，不修改 adapter。
