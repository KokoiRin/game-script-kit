## Context

当前脚本语言已经从单层动作列表演进为 `Step` 树：`Click`、`Drag`、`Wait` 是原子动作步骤，`Repeat` 是控制流步骤。runner 负责解释步骤树，并把原子动作转换为 `InputDevice` 调用。单点取色能力已经通过 `Color` 值对象和 `PixelColorReader` 端口接入，但目前只服务于坐标记录工具，尚未进入脚本运行时。

这个变更的关键约束是维持模块边界：领域层只能表达平台无关模型，runner 只能依赖端口，adapter 只在 CLI 组装处接入，脚本定义仍集中在 `scripts_manager`。

## Goals / Non-Goals

**Goals:**

- 增加可复用的条件模型，让颜色判断成为一种条件，而不是专用分支动作。
- 增加 `If` 控制流步骤，按条件结果选择执行 `then_steps` 或 `else_steps`。
- 复用现有 `PixelColorReader` 端口评估颜色条件，保持取色能力和输入设备动作分离。
- 保证条件分支可以通过单元测试和 `star run <name> --dry-run` 验证。
- 保持 Python-hosted DSL，不引入外部脚本格式。

**Non-Goals:**

- 不实现完整表达式语言、运行时变量、赋值、脚本解析器或用户自定义函数。
- 不实现 `And`、`Or`、`Not`、`Until`、`While`、`break`、`continue`。
- 不做区域取色、平均色、多点采样、图像识别或 OCR。
- 不把取色方法加入 `InputDevice`。
- 不改变现有 `Click`、`Drag`、`Wait`、`Repeat` 行为。

## Decisions

### Decision 1: 条件模型独立于动作步骤

新增 `domain.conditions`，第一版只提供：

```python
@dataclass(frozen=True, slots=True)
class ColorIs:
    point: Point
    expected: Color
    tolerance: int = 0
```

并定义 `Condition = ColorIs` 类型别名。`If` 引用 `Condition`，而不是把颜色字段直接塞进分支步骤。

Rationale:

- `ColorIs` 是判断，`If` 是控制流，两者生命周期不同。分开后未来可以新增其他条件，而不需要新增 `IfColor`、`IfKey`、`IfImage` 等重复分支类型。
- 领域对象仍只保存 `Point`、`Color` 和容差等平台无关数据，不依赖 adapter。

Alternative considered:

- 新增 `IfColor(point, expected, then_steps, else_steps)`。拒绝原因：短期简单但把颜色判断和分支控制流绑死，后续每种判断都会扩展出一个专用分支类型。

### Decision 2: 颜色匹配使用每通道容差

`ColorIs.tolerance` 表示 RGB 三个通道允许的最大绝对差值，必须在 0 到 255 之间。条件成立当且仅当读取颜色的每个通道都落在期望颜色的容差范围内。

Rationale:

- 游戏画面受抗锯齿、亮度或截图后端影响，完全相等经常过脆。
- 每通道绝对差简单、可预测、容易测试，适合作为第一版。

Alternative considered:

- 使用欧氏距离或感知色差。拒绝原因：第一版不需要复杂颜色科学，且用户手写脚本时更难直觉判断阈值。

### Decision 3: `If` 是控制流步骤，分支步骤必须非空

新增 `If(condition, then_steps, else_steps=())`。`then_steps` 必须非空，`else_steps` 可以为空，表示条件不满足时跳过。`then_steps` 和 `else_steps` 都允许继续嵌套 `Repeat` 或 `If`。

Rationale:

- `If` 和 `Repeat` 同属控制流步骤，应进入 `Step` 类型别名并由 runner 解释。
- 要求 `then_steps` 非空可以尽早暴露“分支没有行为”的脚本错误；空 `else_steps` 是常见的“满足才执行”表达。

Alternative considered:

- 要求 `else_steps` 也非空。拒绝原因：会让简单条件动作必须写无意义等待或空动作。

### Decision 4: runner 注入颜色读取端口并委托条件评估

`ScriptRunner` 构造时新增可选 `color_reader: PixelColorReader | None`。遇到 `If` 时 runner 不直接实现完整条件判断，而是调用 `engine.condition_evaluator.evaluate_condition(...)`：

- 先通过脚本窗口解析 `ColorIs.point` 为屏幕坐标。
- 通过 `PixelColorReader.read_color(screen_point)` 读取颜色。
- 根据容差判断真假。
- 根据结果递归执行对应分支步骤。

如果脚本包含颜色条件但 runner 没有注入 `color_reader`，条件评估模块抛出清晰 `RuntimeError`。

Rationale:

- runner 负责解释步骤树，但不应该承载每种条件的完整校验和比较细节。
- 条件评估模块是 engine 层运行时逻辑，可以同时处理端口缺失校验、窗口解析和具体条件判断。
- 取色通过端口注入，领域层和脚本定义不依赖平台 adapter。
- `InputDevice` 继续只表达点击、拖拽、等待，职责不扩大。

Alternative considered:

- 让 `ColorIs` 自己带 `evaluate(reader)` 方法。拒绝原因：会把运行时端口调用放进领域值对象，降低纯数据模型的可测试性和可序列化潜力。
- 把条件评估全部留在 `ScriptRunner` 私有方法里。拒绝原因：runner 会快速膨胀成“步骤解释 + 条件解释 + 依赖校验”的混合类。

### Decision 5: dry-run 使用可预测的颜色 reader

新增一个 dry-run 颜色 reader。第一版通过 CLI 参数 `--dry-run-color #RRGGBB` 提供固定返回值，默认值为 `#000000`。`star run <name> --dry-run` 会同时注入 `DryRunInputDevice` 和该颜色 reader。

Rationale:

- 分支脚本的 dry-run 必须可重复，否则只能测试真实屏幕状态。
- 固定颜色 reader 足够覆盖 CLI 路径和示例脚本，不需要读取真实屏幕。
- 参数化颜色让用户可以手动验证 then/else 两条分支。

Alternative considered:

- dry-run 下直接跳过条件分支。拒绝原因：这会让最重要的控制流行为无法通过 CLI 验证。

### Decision 6: 示例脚本进入默认 catalog

新增 `conditional-color-demo` 脚本，使用 `If(ColorIs(...))` 分支到不同点击/等待序列，并注册进默认 catalog。

Rationale:

- 仓库现有控制流变更都通过具名脚本让用户可以 `star run <name> --dry-run` 验证。
- 示例脚本也能作为 CLI transcript 测试的稳定载体。

### Decision 7: 脚本运行需求分析放在 engine 独立模块

新增 `engine.script_requirements.inspect_script_requirements(script)`，返回脚本执行前的端口需求，例如 `needs_color_reader`。CLI 只根据这个结果决定是否组装 dry-run 或真实取色 adapter，不直接递归扫描 `If`、`Repeat`、`ColorIs` 等脚本步骤树。

Rationale:

- CLI 属于入口和 adapter 组装层，不应理解脚本 AST 细节。
- `engine.condition_evaluator` 仍保留运行时兜底：执行到 `ColorIs` 但没有注入 `color_reader` 时抛出清晰错误。
- 需求分析和执行解释都属于 engine 关注点，但拆成独立模块能避免把 adapter 组装决策塞进 runner 主类。

Alternative considered:

- 把是否需要颜色端口的扫描方法放进 `ScriptRunner`。拒绝原因：runner 的职责是执行脚本，不应该同时承担“为外部组装 adapter 提供静态分析”的 API。

## Risks / Trade-offs

- [Risk] 真实屏幕取色需要 macOS 屏幕录制权限。→ Mitigation: 继续复用现有桌面取色 adapter 的 setup 错误报告；CLI 只在真实运行时延迟加载 adapter。
- [Risk] 分支使 dry-run 输出依赖条件结果。→ Mitigation: dry-run 使用固定颜色 reader，并提供 `--dry-run-color` 覆盖。
- [Risk] 条件模型后续扩展可能膨胀。→ Mitigation: 第一版只实现 `ColorIs` 和 `If`，不提前引入复杂表达式组合。
- [Risk] runner 构造参数增加可能影响现有调用方。→ Mitigation: `color_reader` 使用可选默认值，非分支脚本保持原行为。
- [Risk] 条件评估逻辑留在 runner 内会让 runner 继续膨胀。→ Mitigation: 通过 `engine.condition_evaluator` 集中处理条件评估和运行时依赖校验。
- [Risk] CLI 直接扫描步骤树会让入口层耦合领域控制流细节。→ Mitigation: 通过 `engine.script_requirements` 集中分析脚本端口需求，CLI 只消费分析结果。

## Migration Plan

- 现有脚本不需要迁移，`Click`、`Drag`、`Wait`、`Repeat` 行为保持不变。
- 现有 `ScriptRunner(device=...)` 调用继续可用；只有执行颜色条件分支脚本时才需要注入 `color_reader`。
- CLI 默认真实运行会组装真实取色 adapter；dry-run 会组装固定颜色 reader。

## Open Questions

- 第一版不提供 `And/Or/Not`。如果后续脚本大量出现复合判断，再在 `Condition` 类型下增量扩展。
