## Why

当前图片脚本必须直接写 `ImageTemplate("assets/start.png")`，脚本作者要反复维护文件路径。点位别名已经让固定坐标有了名称，本轮把同样的命名能力扩展到图片模板，让脚本可以用“开始按钮”这类稳定名称引用图片。

## What Changes

- 新增命名图片模型和 `ImageRef`。
- 扩展 `TargetCatalog`，支持解析图片别名到 `ImageTemplate`。
- 扩展 `ImageExists` 和 `ImageTarget`，允许直接接收 `ImageRef`。
- 扩展 runner、condition evaluator 和脚本需求分析，使命名图片能走现有 `ScreenImageLocator` 端口。
- 不实现匹配结果显式获取、anchor 点位、offset 或外部资源文件。

## Capabilities

### New Capabilities

- `image-aliases`: 覆盖图片模板的命名、引用、解析，以及在图片存在条件和图片目标点击中的使用。

### Modified Capabilities

- `script-action-model`: 图片存在条件和图片目标支持命名图片引用。
- `game-script-core`: runner 和条件评估支持执行命名图片引用。
- `screen-image-matching`: 图像定位端口继续只接收解析后的 `ImageTemplate`。

## Impact

- 影响 `src/game_automation/portable/domain/point_aliases.py`，扩展为通用目标资源目录。
- 影响 `conditions.py`、`targets.py`、`condition_evaluator.py`、`runner.py`、`script_requirements.py`。
- 新增命名图片领域测试、条件测试、runner 测试和需求分析测试。
- 不新增平台依赖，不修改 desktop image matching adapter。
