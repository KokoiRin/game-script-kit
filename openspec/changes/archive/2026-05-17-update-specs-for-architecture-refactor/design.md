## Context

架构重构后的代码结构：

```
src/game_automation/
├── domain/           # 纯领域数据模型（无平台依赖）
│   ├── actions.py    # Click, Drag, Wait, Action 类型别名
│   ├── geometry.py   # Point, Rect
│   ├── script.py     # Script
│   └── windows.py    # Window(Protocol), ScreenWindow, AreaWindow
├── engine/           # 执行引擎
│   ├── ports.py      # InputDevice, PointerPositionReader, KeyStateReader 协议
│   └── runner.py     # ScriptRunner
├── adapters/         # 平台 adapter 实现
│   ├── desktop/      # 跨桌面通用实现（PointerPosition, TerminalKeyboard）
│   ├── macos/        # macOS 专用实现（PointerDevice）
│   └── dry_run.py    # 测试用 DryRunInputDevice
├── scripts_manager/  # 脚本定义与管理
│   ├── catalog.py    # ScriptCatalog
│   ├── demo.py       # demo 脚本
│   └── recorded_clicks.py
└── tools/            # 独立工具
    └── coordinate_recorder.py
```

旧结构（已删除）：
- `core/` — 已拆分为 `domain/` + `engine/`
- `scripts/` — 已重命名为 `scripts_manager/`

## Goals / Non-Goals

**Goals:**
- 同步 5 个 spec 文件中的包路径和模块引用，使其反映当前代码结构
- 补充 `input-device-adapter` spec 中缺失的 `DryRunInputDevice` 描述

**Non-Goals:**
- 不修改任何 spec 的行为需求
- 不添加新功能或新需求
- 不修改代码

## Decisions

- **Delta 方式更新**：所有 spec 变更使用 `MODIFIED Requirements` 方式，保留完整需求内容并更新其中过时的模块引用。不新增或删除需求。
- **仅路径更新**：对于纯路径变更（如 `core.ports` → `engine.ports`），保持需求描述和场景不变，仅修改正文中的包名引用。
- **补充描述**：`input-device-adapter` 新增 `DryRunInputDevice` 需求，描述其作为测试用假设备的行为。

## Risks / Trade-offs

- 风险极低：仅文档变更，不影响任何运行代码
