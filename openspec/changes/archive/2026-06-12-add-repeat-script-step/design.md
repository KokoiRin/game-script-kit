## Context

当前脚本语言由 `Script.actions: tuple[Action, ...]` 表达，`Action` 只包含 `Click`、`Drag`、`Wait`。`ScriptRunner` 对这三个类型做单层 `for` 循环分发，并把点击、拖拽、等待转换为 `InputDevice` 调用。

这个模型足够表达固定顺序动作，但不能表达重复一段步骤。后续颜色判断和分支也会继续引入“控制流节点”，它们不是设备动作。为了避免把控制流伪装成 `Action`，本变更先将脚本语言整理为 `Step` 树，并只实现固定次数重复。

## Goals / Non-Goals

**Goals:**
- 将脚本顶层字段从 `actions` 整理为 `steps`，让脚本保存可嵌套步骤树。
- 保留 `Click`、`Drag`、`Wait` 作为原子步骤，并新增 `Repeat(times, steps)` 控制流步骤。
- 让 `ScriptRunner` 能递归执行 `Repeat` 内部步骤，保持原有窗口坐标解析和 `InputDevice` 端口边界。
- 让现有脚本定义、测试和 README 全部迁移到 `steps` 术语。

**Non-Goals:**
- 不实现颜色判断、条件分支、`Until`、无限循环、`break` 或 `continue`。
- 不引入 YAML/JSON 外部 DSL；脚本仍先使用 Python-hosted DSL 构造领域对象。
- 不改变 `InputDevice`、macOS adapter、dry-run adapter 的端口方法。
- 不引入运行时变量、表达式求值器或脚本解析器。

## Decisions

### 使用 Step 作为脚本语言的统一节点

`Click`、`Drag`、`Wait` 仍然表达对设备的原子操作，但脚本顶层不再称为 `actions`。新增 `Step` 类型别名，覆盖 `Click | Drag | Wait | Repeat`。如需保留“原子动作”的概念，可在内部使用 `PrimitiveAction = Click | Drag | Wait`，但公开脚本 DSL 以 `steps` 为主。

替代方案：继续叫 `Action` 并把 `Repeat` 加入 `Action`。这个方案短期改动少，但会让控制流和设备动作混在一起。后续加入 `If` 后，`Action` 的含义会进一步变弱。

### Repeat 使用 `times` 和 `steps`

`Repeat` 第一版字段为：

```python
Repeat(
    times=3,
    steps=(
        Click(Point(100, 200)),
        Wait(0.5),
    ),
)
```

- `times: int` 表示重复次数。
- `steps: tuple[Step, ...]` 表示每次重复执行的步骤序列。
- `times` MUST 大于 0。
- `steps` MUST 非空。
- `Repeat` 内部允许继续嵌套 `Repeat`。

替代方案：允许 `times=0` 表示跳过。这个方案对配置开关友好，但脚本自动化里更容易隐藏错误。第一版拒绝 0，让“没执行”尽早暴露。

替代方案：用 `count`、`repeat` 或 `iterations` 命名。`times` 更贴近日常 DSL 写法，也和 `Repeat(times=3, steps=...)` 读起来最直接。

### Runner 改为递归解释步骤树

`ScriptRunner.run(script)` 仍是唯一执行入口。内部新增 `_run_steps(script, steps)` 递归遍历：

- 遇到 `Click` / `Drag` / `Wait` 时保持现有行为。
- 遇到 `Repeat` 时执行 `times` 轮，每轮按顺序执行其内部 `steps`。
- 未知步骤类型仍抛出清晰 `TypeError`。

这个设计不需要修改 `InputDevice`。dry-run 和 fake device 仍只观察最终展开后的设备操作。

### 现在做破坏性迁移，不保留长期兼容字段

项目还小，现有脚本定义集中在 `scripts_manager`，测试也能一次性迁移。第一版直接把 `Script.actions` 改为 `Script.steps`，避免同时维护 `actions` 和 `steps` 两套字段。

替代方案：暂时同时支持 `actions` 和 `steps`。这个方案对外部使用者更温和，但会让领域模型构造规则、错误信息和文档重复。当前仓库没有稳定外部 API，直接迁移更清晰。

## Risks / Trade-offs

- [Risk] `Action` 到 `Step` 的术语迁移会触及较多测试和 README → Mitigation: 一次性更新脚本定义、测试断言和文档，并用 `rg "actions|Action"` 做残留检查。
- [Risk] 递归执行可能在深层嵌套时难以调试 → Mitigation: 第一版只支持固定次数 `Repeat`，测试覆盖嵌套 Repeat 的展开顺序。
- [Risk] `Repeat(times)` 可能被设置得很大导致真实设备执行时间过长 → Mitigation: 第一版只做领域校验，不引入全局执行预算；后续如果需要再加 runner 级安全策略。
- [Risk] 直接移除 `Script.actions` 会破坏未更新的脚本定义 → Mitigation: 仓库内脚本集中迁移，CLI smoke 测试覆盖默认脚本。
