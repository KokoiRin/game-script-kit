## Why

现有脚本已经可以通过 `ColorIs(point)` 和 `WaitUntil` 读取单点颜色，但真实自动化里更常见的是判断某个按钮、图标或状态块是否出现在屏幕上。先建立平台无关的图像匹配端口，可以延续 `PixelColorReader` 的 screen adapter 边界，并为后续 `ImageExists(...)` 和按图片定位点击打基础。

## What Changes

- 新增屏幕图像匹配能力，用平台无关模型表达待查找图片、搜索区域、最低匹配置信度和匹配结果。
- 在 engine ports 中新增独立图像定位端口，用于在当前屏幕中查找模板图片并返回匹配区域、中心点和置信度。
- 新增桌面/macOS 可用的 adapter，通过现有桌面截图能力获取屏幕图像，并在 adapter 内完成模板匹配。
- 新增 dry-run/fake 友好的测试替身和 adapter contract 测试，确保核心代码不依赖真实屏幕或 macOS 权限。
- 本 change 不新增 `ImageExists(...)` 条件，不改变脚本动作模型，也不实现按图片点击；这些能力将基于本端口在后续 change 中接入。

## Capabilities

### New Capabilities
- `screen-image-matching`: 定义屏幕模板图像匹配的领域模型、engine port、桌面 adapter 行为和错误边界。

### Modified Capabilities
- 无。

## Impact

- 受影响代码：`src/game_automation/portable/domain/`、`src/game_automation/portable/engine/ports.py`、`src/game_automation/platform/desktop/adapters/`、`src/game_automation/portable/adapters/`、相关测试。
- 依赖影响：第一版优先复用 `pyautogui.screenshot()` 与 Pillow 图像对象；是否引入 OpenCV 作为更强匹配后端由 design 明确。
- 架构影响：图像识别保持为独立 screen port，不并入 `InputDevice`，且领域层/engine 层不得导入 macOS、pyautogui 或 OpenCV。
