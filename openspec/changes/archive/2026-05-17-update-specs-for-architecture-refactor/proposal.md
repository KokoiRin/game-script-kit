## Why

近期架构重构将 `core/` 拆分为 `domain/`（纯领域模型）和 `engine/`（执行引擎），并将 `scripts/` 重命名为 `scripts_manager/`。现有 spec 文件中的包路径、模块引用仍指向旧结构，需要同步更新以保持文档与代码一致。

## What Changes

- 更新 `game-script-core` spec：将 "core workflow"、"core runner" 等过时引用改为 `engine.ScriptRunner`、`engine.ports.InputDevice` 等当前模块路径
- 更新 `script-action-model` spec：将领域模型所在包从隐含的 core 改为明确的 `domain` 包（`domain.actions`、`domain.geometry`、`domain.script`、`domain.windows`）
- 更新 `input-device-adapter` spec：端口定义位置从 `core.ports` 改为 `engine.ports`；补充 `DryRunInputDevice` 作为测试用 adapter 实现
- 更新 `script-management` spec：`ScriptCatalog` 和 demo 脚本位置从 `scripts/` 改为 `scripts_manager/`
- 更新 `coordinate-recorder-tool` spec：adapter 端口引用同步到 `engine.ports`

## Capabilities

### New Capabilities
<!-- 本次仅为文档同步，无新增能力 -->

### Modified Capabilities
- `game-script-core`: 更新执行引擎和端口引用的包路径，无行为变更
- `script-action-model`: 更新领域模型包路径引用，无行为变更
- `input-device-adapter`: 更新端口定义位置；补充 DryRunInputDevice 描述
- `script-management`: 更新脚本管理模块路径引用，无行为变更
- `coordinate-recorder-tool`: 更新端口引用路径，无行为变更

## Impact

- 所有 5 个 spec 文件（`openspec/specs/*/spec.md`）将被更新
- 无代码变更，仅文档同步
- 无 API 变更，无破坏性变更
