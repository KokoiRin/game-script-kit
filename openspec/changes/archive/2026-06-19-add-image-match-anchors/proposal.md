## Why

当前图片目标点击只能使用匹配中心点。实际游戏里常需要点击图标的右边中点、底边中点或角点，因此在做 offset 前，先明确“从匹配结果取哪个点”的 anchor 语义。

## What Changes

- 新增图片匹配 anchor 点位计算，覆盖中心、四边中点和四角。
- 扩展 `ImageLookupResult` 和 `ImageMatch`，可以按 anchor 返回点位。
- 扩展 `ImageTarget`，允许指定 anchor，默认仍为 `center`。
- 扩展 runner 图片目标解析，点击指定 anchor 点位。
- 不新增 offset 模型，不改变现有默认中心点行为。

## Capabilities

### New Capabilities

- `image-match-anchors`: 覆盖图片匹配结果 anchor 点位获取。

### Modified Capabilities

- `script-action-model`: `ImageTarget` 新增 anchor 字段，默认中心点。
- `game-script-core`: runner 图片目标点击使用 anchor 点位。

## Impact

- 影响 `domain.image_matching`、`domain.targets` 和 runner 图片目标解析。
- 增加领域模型和 runner 测试。
- 不新增平台依赖，不修改 desktop adapter。
