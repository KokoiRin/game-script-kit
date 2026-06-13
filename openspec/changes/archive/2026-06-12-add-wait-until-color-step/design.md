## Context

当前脚本语言已经有三类原子动作步骤 `Click`、`Drag`、`Wait`，以及两个控制流步骤 `Repeat` 和 `If`。条件判断由 `domain.conditions` 表达，运行时评估由 `engine.condition_evaluator` 处理，脚本执行前的端口需求由 `engine.script_requirements` 分析，CLI 只根据需求组装 adapter。

`WaitUntil(ColorIs(...))` 应该复用这条边界：它是控制流步骤，不是输入设备动作；它等待的是条件，不直接读取屏幕；它通过 runner 调用条件评估器，并通过 `InputDevice.wait()` 控制轮询间隔。

## Goals / Non-Goals

**Goals:**

- 新增 `WaitUntil(condition, timeout_seconds, interval_seconds)` 控制流步骤。
- 让 `ScriptRunner` 在条件满足前按固定间隔轮询，满足后继续执行后续步骤。
- 超时后抛出清晰 `TimeoutError`，避免脚本静默继续。
- 保持 `condition_evaluator` 负责条件评估和端口缺失错误。
- 保持 `script_requirements` 负责递归识别颜色读取端口需求。
- 增加一个可通过 `star run <name> --dry-run` 验证的示例脚本，并在 README 留下端到端验证方法。

**Non-Goals:**

- 不实现组合条件、表达式语言、运行时变量、`break/continue`。
- 不实现无限等待；第一版必须有正数 timeout。
- 不新增真实时间源、定时器 adapter 或异步执行模型。
- 不修改 `InputDevice`、`PixelColorReader` 或平台 adapter 接口。
- 不做全局执行预算；这里只处理 `WaitUntil` 自身的 timeout。

## Decisions

### Decision 1: `WaitUntil` 作为控制流步骤

新增领域模型：

```python
@dataclass(frozen=True, slots=True)
class WaitUntil:
    condition: Condition
    timeout_seconds: float
    interval_seconds: float
```

`timeout_seconds` 和 `interval_seconds` 都必须大于 0。`WaitUntil` 加入 `Step` 类型别名，允许出现在顶层、`Repeat` 内部、`If` 分支内，后续如果需要也可以被嵌套在其他控制流中。

Rationale:

- `WaitUntil` 不直接表达设备动作，而是解释一段运行时控制流。
- 正数 timeout 能避免第一版出现不可退出脚本。

Alternative considered:

- 用 `Repeat(times, steps=(If(...), Wait(...)))` 手写等待。拒绝原因：不能表达“满足后立即跳出”，也不能自然报告超时。

### Decision 2: runner 使用 `InputDevice.wait()` 推进轮询

runner 执行 `WaitUntil` 时：

1. 立即评估一次条件。
2. 如果条件为真，直接继续后续步骤，不等待。
3. 如果条件为假且尚未达到 timeout，调用 `device.wait(interval_seconds)`。
4. 重复评估，直到条件为真或超时。
5. 超时抛出 `TimeoutError`。

Rationale:

- 复用现有 `InputDevice.wait()`，不新增定时器或 sleep port。
- fake device 和 dry-run device 都可以观测等待次数和间隔。
- 立即评估一次符合“已经满足就不等待”的脚本直觉。

Alternative considered:

- 用真实时间 `time.monotonic()` 控制 timeout。拒绝原因：测试会变慢，也会引入真实时间源抽象；当前脚本 wait 已经通过 `InputDevice.wait()` 表达等待。

### Decision 3: timeout 使用预算累加而不读真实时钟

第一版用已请求等待的累计时长判断 timeout。每轮最多等待 `min(interval_seconds, remaining_timeout)`，这样不会等待超过 timeout。等待后再次评估，如果仍不满足且预算耗尽，则抛 `TimeoutError`。

Rationale:

- 行为完全可测试，不依赖真实时钟精度。
- dry-run 输出能稳定展示最多等待到 timeout。
- 不会因为 interval 大于 timeout 而等待过长。

Alternative considered:

- 等待固定 interval，可能超过 timeout。拒绝原因：用户写 `timeout=1, interval=5` 时会实际等待 5 秒，违背 timeout 语义。

### Decision 4: 端口需求分析递归识别 `WaitUntil`

`engine.script_requirements` 增加对 `WaitUntil.condition` 的检查。只要条件直接或间接需要颜色读取端口，CLI 就注入 dry-run 或真实 `PixelColorReader`。

Rationale:

- CLI 不理解脚本 AST 细节，只消费 `ScriptRequirements`。
- 端口需求分析属于 engine 层运行前分析，不放进 runner。

### Decision 5: 示例脚本与 README 端到端验证

新增 `wait-until-color-demo`，默认 dry-run 颜色不满足条件时会输出等待直到 timeout 并失败；指定匹配颜色时会立即通过并继续点击。README 记录两条端到端命令：

- 成功路径：`star run wait-until-color-demo --dry-run --dry-run-color #102030`
- 超时路径：`star run wait-until-color-demo --dry-run`

Rationale:

- 和 `repeat-demo`、`conditional-color-demo` 一样，新增控制流必须有可直接运行的具名脚本。
- 成功与超时两条路径都能在 dry-run 下稳定验证。

## Risks / Trade-offs

- [Risk] 使用累计 wait 预算不等于真实墙钟时间。→ Mitigation: 当前脚本等待本来通过 `InputDevice.wait()` 表达；这是第一版最可测、最符合现有架构的语义。
- [Risk] timeout 抛错会中断脚本。→ Mitigation: 这是显式失败，比静默继续更安全；测试和 README 覆盖超时路径。
- [Risk] runner 继续增加控制流分发。→ Mitigation: runner 只识别 `WaitUntil` 类型和调用 condition evaluator，不承载条件评估细节。

## Migration Plan

- 现有脚本不需要迁移。
- 现有 `ScriptRunner(device=...)` 调用继续可用；只有执行颜色条件等待脚本时需要 color reader。
- CLI 通过 `script_requirements` 自动注入需要的 color reader。

## Open Questions

- 是否需要后续支持成功/超时分支，例如 `WaitUntil(..., on_timeout_steps=...)`。第一版不做，先让失败显式抛出。
