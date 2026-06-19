## Why

当前脚本里的固定点击位置只能写成裸 `Point(x, y)`。游戏按钮位置一多，脚本会变成一组难以理解和维护的坐标数字，因此先引入点位别名，让代码脚本可以用“头像”“背包”这类稳定名称表达固定坐标。

## What Changes

- 新增命名点位模型，用名称绑定固定 `Point`。
- 新增脚本资源目录，用于解析 `PointRef("头像")` 这类点位引用。
- 扩展 `Click` 点击目标，使其兼容命名点位引用。
- 扩展 runner 点击解析，使命名点位在执行时解析成现有 `Point`，并继续应用脚本窗口坐标规则。
- 不涉及图片别名、图片匹配、anchor、offset、UI 管理或外部脚本文件。

## Capabilities

### New Capabilities

- `point-aliases`: 覆盖固定点位的命名、引用、解析和点击执行语义。

### Modified Capabilities

- `script-action-model`: `Click` 新增命名点位引用作为合法点击目标。
- `game-script-core`: `ScriptRunner` 新增命名点位点击解析语义。

## Impact

- 影响 `src/game_automation/portable/domain/` 中的点击目标和脚本资源模型。
- 影响 `src/game_automation/portable/engine/runner.py` 的点击目标解析。
- 新增底层行为测试和 runner 测试。
- 不新增平台依赖，不修改真实鼠标、截图或图像匹配 adapter。
