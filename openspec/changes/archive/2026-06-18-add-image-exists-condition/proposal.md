## Why

已有 `ScreenImageLocator` 可以在 adapter 层查找模板图片，但脚本还不能把“某个图片是否出现在屏幕上”作为条件使用。新增 `ImageExists(...)` 能让现有 `If` 和 `WaitUntil` 直接表达更接近真实自动化的屏幕状态识别。

## What Changes

- 在条件领域模型中新增 `ImageExists`，记录模板图片、可选搜索区域和最低匹配置信度。
- 扩展条件评估模块，使 `ImageExists` 通过 `ScreenImageLocator` 端口判断模板是否存在。
- 扩展 `ScriptRunner`、应用层和 CLI 装配，使包含图片条件的脚本能在 dry-run 和真实本地桌面模式下运行。
- 新增一个可 dry-run 验证的命名示例脚本，用于演示 `WaitUntil(ImageExists(...))` 成功与超时路径。
- 本 change 不实现按图片定位点击，不新增 `ImageTarget`，也不做多结果匹配或 OCR。

## Capabilities

### New Capabilities
- 无。

### Modified Capabilities
- `script-action-model`: 新增平台无关的 `ImageExists` 条件模型。
- `game-script-core`: runner 通过 `ScreenImageLocator` 端口评估图片存在条件，并让 `If`/`WaitUntil` 复用该条件。
- `script-management`: CLI/application 在 dry-run 和真实运行时为图片条件脚本注入图像定位能力，并提供可运行示例脚本。

## Impact

- 受影响代码：`src/game_automation/portable/domain/conditions.py`、`src/game_automation/portable/engine/condition_evaluator.py`、`src/game_automation/portable/engine/runner.py`、`src/game_automation/portable/engine/script_requirements.py`、`src/game_automation/portable/application/script_run.py`、本地桌面 composition、CLI tests、脚本 catalog 和 README。
- 新增行为依赖已归档的 `ScreenImageLocator` / `ImageTemplate` / `ImageMatch`。
- 不新增新的平台依赖；真实匹配继续由 `PyAutoGuiScreenImageLocator` adapter 负责。
