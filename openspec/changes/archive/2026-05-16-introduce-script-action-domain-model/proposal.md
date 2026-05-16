## Why

当前核心层只有固定 demo workflow，还不能表达用户已经拼装好的脚本。需要先建立一组小而明确的领域概念，让脚本可以由多个可执行动作组成，并让点击、拖拽依赖清晰的窗口和坐标模型。

## What Changes

- 新增脚本领域模型：`Script` 表示一组按顺序编排的动作。
- 新增动作模型：`Click`、`Drag`、`Wait` 分别表达点击、拖拽和等待。
- 新增窗口模型：`ScreenWindow` 表示整个屏幕，`AreaWindow` 表示指定区域。
- 新增几何模型：`Point` 表示动作位置，`Rect` 表示区域范围。
- 新增脚本运行语义：脚本运行一次时按顺序执行所有动作，点击和拖拽在对应窗口内解析位置。
- 不引入循环、条件判断、图像识别、脚本文件格式或自动窗口查找。

## Capabilities

### New Capabilities

- `script-action-model`: 定义脚本、动作、窗口、点和矩形的领域模型，以及脚本执行一次时的基础行为。

### Modified Capabilities

- `game-script-core`: 将核心 workflow 的规格扩展为支持脚本动作模型，而不是只表达固定 demo workflow。

## Impact

- 影响 `src/game_automation/core/` 下的核心模型和 workflow/runner 组织。
- 现有 `InputDevice` adapter 边界保持不变，macOS adapter 不需要感知脚本领域对象。
- 现有 demo 可改为通过新脚本模型构造，保持 dry-run 和测试替身可用。
