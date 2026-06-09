## Context

当前项目使用 port-and-adapter 结构：`domain` 保存平台无关的数据模型，`engine.ports` 定义业务层依赖的端口，`adapters` 提供平台实现，`tools.coordinate_recorder` 作为独立业务工具通过端口读取鼠标坐标和按键状态。

坐标记录工具现在只通过 `PointerPositionReader` 读取并打印 `Point`。用户想写游戏脚本时，通常还需要知道某个点的屏幕颜色。这个变更先把单点取色接入坐标记录工具，不改变脚本动作模型和 `ScriptRunner`，为后续颜色判断或分支能力打基础。

## Goals / Non-Goals

**Goals:**

- 保持现有结构：通用逻辑放在领域层和业务工具层，平台相关实现通过 port 接入。
- 新增平台无关的 RGB 颜色值对象。
- 新增平台无关的单点颜色读取端口。
- 新增 pyautogui/桌面 adapter，用于读取指定屏幕点颜色。
- 让 `CoordinateRecorder` 在打印当前坐标、按 `1` 记录、结束汇总时同时包含颜色。
- 保持 `star recorder` 作为入口，不增加新的脚本动作。

**Non-Goals:**

- 不实现脚本分支、颜色判断 action 或条件表达式。
- 不修改 `ScriptRunner` 执行语义。
- 不做区域取色、平均色、多点采样、图像识别或 OCR。
- 不新增外部脚本格式。
- 不新增第三方依赖。

## Decisions

### Decision 1: `Color` 放在 `domain`

新增 `src/game_automation/domain/color.py`，定义不可变 `Color(red, green, blue)` 值对象；对外字符串展示为 `#RRGGBB`，并支持 `Color.from_hex("#RRGGBB")` 参数形式；在 `domain/__init__.py` 导出。

Rationale:

- RGB 颜色是平台无关概念，和 `Point`、`Rect` 一样属于领域值对象。
- 后续脚本颜色判断可以直接复用同一个模型。

Alternative considered:

- 直接使用 `(r, g, b)` tuple。拒绝原因：tuple 缺少字段语义和范围校验，后续条件模型可读性较差。

### Decision 2: 新增独立 `PixelColorReader` port

在 `engine.ports` 中新增：

```python
class PixelColorReader(Protocol):
    def read_color(self, point: Point) -> Color: ...
```

Rationale:

- 取色是屏幕读取能力，不属于 `InputDevice` 的点击/拖拽/等待职责。
- 独立 port 让业务工具只依赖抽象，平台截图逻辑留在 adapter。
- 未来脚本分支、颜色断言或其他工具可以复用该 port。

Alternative considered:

- 把取色方法加到 `PointerPositionReader`。拒绝原因：读取当前位置和读取任意点颜色是不同职责；合并会让实现和测试变重。

### Decision 3: 桌面取色 adapter 放在 `adapters/desktop/`

新增 `src/game_automation/adapters/desktop/pixel_color.py`，实现 `PyAutoGuiPixelColorReader`。

Rationale:

- 当前 `PyAutoGuiPointerPositionReader` 已经放在 `adapters/desktop/`，取色同样是 pyautogui 提供的桌面通用能力。
- macOS 专用鼠标输入仍保留在 `adapters/macos/`。

Adapter 通过延迟导入 pyautogui 保持模块可导入性；读取失败时抛出清晰 `RuntimeError`，提示检查依赖或屏幕录制/自动化权限。

### Decision 4: 坐标记录器记录 `RecordedPoint` 而不是只记录 `Point`

新增领域或工具层记录模型：

```python
@dataclass(frozen=True, slots=True)
class RecordedPoint:
    point: Point
    color: Color
```

建议把它放在 `tools.coordinate_recorder`，因为它是记录工具的输出形状，不一定是通用领域概念。

Rationale:

- 保留 `Point` 和 `Color` 各自语义，避免用二元 tuple。
- 测试可以直接断言记录里的 point 和 color。
- 后续如果其他工具也需要类似模型，再考虑上移到 domain。

Alternative considered:

- 将 `CoordinateRecorder.recorded` 改为 `list[tuple[Point, Color]]`。拒绝原因：可读性和输出语义较差。

### Decision 5: `CoordinateRecorder` 通过构造注入 `PixelColorReader`

`CoordinateRecorder` 新增必需依赖：

```python
color_reader: PixelColorReader
```

它在显示或记录时先读取当前 `Point`，再调用 `color_reader.read_color(point)` 得到 `Color`。

Rationale:

- 保持业务工具不直接调用平台库。
- 单次显示/记录应该保证颜色对应同一次读取到的点位。
- 测试可以注入 fake reader 覆盖所有行为。

Alternative considered:

- 让 color reader 自己读取鼠标当前位置和颜色。拒绝原因：会让取色 port 混入坐标读取职责，且难以保证测试中的点位传递正确。

## Risks / Trade-offs

- [Risk] `pyautogui.screenshot()` 可能需要 macOS 屏幕录制权限。→ Adapter 捕获异常并报告清晰 setup 错误；README 补充权限说明。
- [Risk] 每秒截图一次可能比读取坐标更重。→ 当前默认 1 秒显示一次、按键触发时额外读取，MVP 可接受；后续如有性能问题再优化为 1x1 截图或平台专用 API。
- [Risk] 记录工具返回值从 `tuple[Point, ...]` 变为 `tuple[RecordedPoint, ...]`，测试和调用方需同步更新。→ 该工具目前是内部 CLI 工具，影响可控；OpenSpec 明确记录输出包含颜色。
- [Risk] `pyautogui.getpixel` 返回 RGB 或 RGBA。→ Adapter 只取前三个通道并构造 `Color`。
