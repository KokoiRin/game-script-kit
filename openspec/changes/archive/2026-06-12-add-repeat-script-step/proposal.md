## Why

当前脚本模型只能表达线性的 `Click` / `Drag` / `Wait` 动作序列，无法复用一段重复操作。下一步要支持分支和循环能力，因此需要先把脚本语言从“动作列表”整理为“可嵌套步骤树”，并以最小控制流节点 `Repeat` 搭好框架。

## What Changes

- **BREAKING**: 将 `Script.actions` 概念整理为 `Script.steps`，顶层脚本保存一组可执行步骤，而不再只保存原子动作。
- 新增 `Repeat(times, steps)` 步骤，用于按固定次数重复执行一组步骤。
- 保留 `Click`、`Drag`、`Wait` 作为原子执行步骤，先不引入颜色判断、条件分支、无限循环、`break` 或 `continue`。
- `ScriptRunner` 从单层动作循环升级为递归解释步骤树，但仍只通过 `InputDevice` 执行真实设备操作。
- 现有脚本定义和 README 示例改用 `steps=(...)`。

## Capabilities

### New Capabilities

### Modified Capabilities
- `script-action-model`: 脚本领域模型从有序动作列表升级为有序步骤树，并新增固定次数重复步骤。
- `game-script-core`: `ScriptRunner` 支持执行包含 `Repeat` 的步骤树，并保持原有 `InputDevice` 边界。

## Impact

- 影响领域模型：`src/game_automation/domain/actions.py`、`src/game_automation/domain/script.py`、`src/game_automation/domain/__init__.py`。
- 影响执行引擎：`src/game_automation/engine/runner.py`。
- 影响脚本定义：`src/game_automation/scripts_manager/*.py` 中 `Script(..., actions=...)` 需要迁移为 `steps=...`。
- 影响文档和测试：README、脚本模型测试、runner 测试、CLI smoke 测试。
- 不新增第三方依赖，不改变 `InputDevice`、macOS adapter 或 dry-run adapter 的端口形态。
