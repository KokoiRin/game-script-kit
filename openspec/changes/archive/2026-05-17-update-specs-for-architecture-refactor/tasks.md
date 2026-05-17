## 1. 更新 game-script-core spec

- [x] 1.1 将 `game-script-core` spec 中的 "core workflow"、"核心层" 等过时措辞替换为 `engine`、`domain`、`scripts_manager` 等当前包名
- [x] 1.2 将 "Core runner" 重命名为 `ScriptRunner`，对齐 `engine.runner` 实现

## 2. 更新 script-action-model spec

- [x] 2.1 在需求描述中标注领域模型的当前包位置（`domain.actions`、`domain.geometry`、`domain.script`、`domain.windows`）

## 3. 更新 input-device-adapter spec

- [x] 3.1 将端口定义引用从隐含的 core 更新为明确的 `engine.ports.InputDevice`
- [x] 3.2 补充 `DryRunInputDevice` 作为测试用 adapter 的需求和场景

## 4. 更新 script-management spec

- [x] 4.1 将 `ScriptCatalog` 和 demo 脚本的包引用从 `scripts/` 更新为 `scripts_manager/`
- [x] 4.2 更新 Purpose 描述

## 5. 更新 coordinate-recorder-tool spec

- [x] 5.1 将端口引用同步到 `engine.ports.PointerPositionReader` 和 `engine.ports.KeyStateReader`
- [x] 5.2 更新 Purpose 描述

## 6. 验证

- [x] 6.1 确认所有 spec 中的包路径与 `src/game_automation/` 实际结构一致
- [x] 6.2 运行 `openspec status --change "update-specs-for-architecture-refactor"` 确认所有 artifact 完成
