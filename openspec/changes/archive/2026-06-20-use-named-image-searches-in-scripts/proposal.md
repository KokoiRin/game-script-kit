## Why

脚本已经支持图片别名、区域别名和搜索规格，但 `ImageExists(...)` 和 `ImageTarget(...)` 仍要求脚本显式携带图片和搜索参数。用户在写游戏脚本时更自然的表达是引用一个搜索名，例如“离开按钮”，由资源目录统一管理图片、区域和置信度。

## What Changes

- `ImageExists(...)` 支持 `SearchRef(...)` 和 `ImageSearchSpec(...)`。
- `ImageTarget(...)` 支持 `SearchRef(...)` 和 `ImageSearchSpec(...)`。
- 搜索别名中的图片、区域和最低置信度会作为默认搜索参数。
- 脚本步骤上显式提供的 `region` 或 `min_confidence` 会覆盖搜索别名默认值。
- 脚本详情、依赖检查和 dry-run 图片依赖能解析搜索别名里的图片。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `image-aliases`: 搜索别名可被脚本图片条件和图片目标引用。
- `game-script-core`: 图片条件和图片目标的执行语义支持搜索别名。
- `local-control-ui`: 脚本详情、依赖检查和 dry-run 图片依赖解析搜索别名。

## Impact

- 影响领域模型、图片查询解析、条件评估、图片目标点击、依赖收集、脚本详情和测试。
- 不新增平台 adapter 能力，不改变 OpenCV 匹配实现。
