## 1. 领域模型

- [x] 1.1 新增 `core/geometry.py`，定义 `Point`、`Rect`，并校验矩形宽度和高度必须为正数。
- [x] 1.2 新增 `core/windows.py`，定义 `ScreenWindow`、`AreaWindow`，支持按明确规则将点解析为屏幕坐标。
- [x] 1.3 新增 `core/actions.py`，定义 `Click`、`Drag`、`Wait`，动作不绑定窗口，也不引入 `Move` 和 `MouseButton`。
- [x] 1.4 新增 `core/script.py`，定义 `Script`，绑定单个窗口并保证动作顺序被保留。

## 2. 脚本运行

- [x] 2.1 新增 `core/ports.py`，定义跨平台 `InputDevice` 端口，点击和拖拽方法不接收鼠标按键参数。
- [x] 2.2 新增 `core/runner.py`，按顺序执行 `Script` 中的所有动作。
- [x] 2.3 runner 执行 `Click` 时，通过脚本级窗口解析点并调用 `InputDevice.click`。
- [x] 2.4 runner 执行 `Drag` 时，通过脚本级窗口解析起止点并调用 `InputDevice.drag_to`。
- [x] 2.5 runner 执行 `Wait` 时，等待指定持续时间，并允许测试注入等待实现。
- [x] 2.6 runner 不支持独立 `Move` 脚本动作；底层 adapter 如需移动指针，由 adapter 内部处理。

## 3. Demo 集成

- [x] 3.1 将现有 demo workflow 改为构造脚本动作模型后交由 runner 执行。
- [x] 3.2 保持 CLI 的 dry-run 和 macOS adapter 选择逻辑不进入核心脚本模型。
- [x] 3.3 将 `core/protocols.py` 的职责迁移到 `core/ports.py`，去除或停止使用旧的泛名入口。
- [x] 3.4 用 `Point` 和动作持续时间替代 `types.py` 中重复的 `Coordinate`、`PointerTiming`、`MouseButton` 概念。
- [x] 3.5 将 `FakeInputDevice` 和 `RecordedAction` 移到 `tests/support/`，避免测试替身出现在产品领域包中。
- [x] 3.6 确保导入核心脚本和 demo 模块不会导入或初始化平台 adapter。

## 4. 测试与验证

- [x] 4.1 添加模型测试，覆盖脚本动作顺序、空脚本拒绝和非法矩形拒绝。
- [x] 4.2 添加窗口坐标解析测试，覆盖屏幕窗口、指定区域窗口，以及区域外点不做边界夹取。
- [x] 4.3 添加动作模型测试，验证第一版不暴露 `Move` 和 `MouseButton`。
- [x] 4.4 添加 runner 测试，验证点击、拖拽、等待动作按顺序映射到 fake device，且点击和拖拽统一使用脚本级窗口解析坐标、不传鼠标按键。
- [x] 4.5 更新 macOS adapter 测试，验证 adapter 内部自行映射为底层左键行为。
- [x] 4.6 运行测试套件、OpenSpec change 校验和 diff hygiene 检查。
