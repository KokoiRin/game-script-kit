## Why

图片别名已经可以被条件和点击目标使用，但“找图片”本身还没有一个可观察的 portable 查询结果。下一步做 anchor 和 offset 前，需要先把图片定位结果显式建模，便于条件、点击、调试和后续坐标计算复用。

## What Changes

- 新增图片匹配查询结果，表示 found/not found，并在找到时暴露 `ImageMatch`、矩形、中心点和置信度。
- 新增 portable 查询函数，负责解析 `ImageTemplate` / `ImageRef` 并调用 `ScreenImageLocator`。
- 让图片存在条件和图片目标点击复用该查询函数。
- 不实现 anchor 点位选择、offset 或匹配结果缓存。

## Capabilities

### New Capabilities

- `image-match-query`: 覆盖图片匹配查询请求、查询结果和未找到语义。

### Modified Capabilities

- `game-script-core`: 条件评估和图片点击通过查询层消费匹配结果。
- `screen-image-matching`: 明确未找到是查询结果，不是平台 setup 错误。

## Impact

- 影响 `src/game_automation/portable/domain/image_matching.py` 和 `src/game_automation/portable/engine/`。
- 增加纯查询测试，并保持现有条件、runner 和 dry-run 行为兼容。
- 不新增平台依赖，不修改 desktop adapter。
