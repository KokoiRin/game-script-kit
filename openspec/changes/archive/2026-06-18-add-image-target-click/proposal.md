## Why

脚本现在可以判断图片是否存在，但仍然只能点击固定坐标。新增图片目标点击可以把“找到按钮图片并点击它”变成脚本原生能力，完成从屏幕状态识别到坐标定位动作的第一条闭环。

## What Changes

- 新增 `ImageTarget` 领域模型，用模板图片、可选搜索区域、最低匹配置信度和可选偏移表达动态点击目标。
- 扩展 `Click`，允许点击目标是静态 `Point` 或动态 `ImageTarget`，保持 `Drag` 暂时只支持静态点。
- 扩展 runner，在执行 `Click(ImageTarget(...))` 时通过 `ScreenImageLocator` 找到匹配结果，解析为最终屏幕坐标后调用现有 `InputDevice.click()`。
- 扩展需求分析、应用层和 CLI/dry-run 配置，使图片目标点击按需注入 image locator，并可通过 dry-run 复现。
- 新增可直接运行的 `click-image-demo`，用于验证 `--dry-run-image` 能把图片目标解析成点击坐标。
- 本 change 不实现拖拽图片目标、多匹配选择、等待后点击组合语法或真实浏览器/截图 smoke。

## Capabilities

### New Capabilities
- 无。

### Modified Capabilities
- `script-action-model`: `Click` 支持 `ImageTarget` 动态目标，保留静态 `Point` 兼容行为。
- `game-script-core`: runner 能把图片目标解析为屏幕坐标并通过 `InputDevice.click()` 执行。
- `script-management`: CLI/application 支持 dry-run 图片目标点击示例和真实运行 image locator 注入。

## Impact

- 受影响代码：`src/game_automation/portable/domain/actions.py`、新增或扩展目标模型、`src/game_automation/portable/engine/runner.py`、`script_requirements.py`、`application/script_run.py`、CLI、脚本 catalog、README 和相关测试。
- 不新增平台依赖；继续复用 `ScreenImageLocator`、`DryRunScreenImageLocator` 和 `PyAutoGuiScreenImageLocator`。
- 兼容性目标：已有 `Click(Point(...))` 脚本不需要修改，dry-run 输出保持不变。
