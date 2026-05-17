## 1. 工具模型与循环

- [x] 1.1 新增 `game_automation.tools` package，用于放置独立开发辅助工具。
- [x] 1.2 新增坐标记录应用服务 `CoordinateRecorder`，组合坐标读取 port、按键状态 port、等待函数和输出函数。
- [x] 1.3 新增坐标记录核心循环，支持每 1 秒输出当前坐标、每 50ms 检查按键状态。
- [x] 1.4 记录坐标时复用 `Point` 模型，并在结束后打印所有记录坐标。
- [x] 1.5 实现按键边沿检测，确保长按 `1` 不重复记录同一按键状态，并在检测到按下边沿时立即重新读取坐标。
- [x] 1.6 明确不新增 `GetCoordinate` 或同类脚本 action，工具不创建或执行 `Script`。

## 2. 平台依赖与 CLI

- [x] 2.1 在 `core/ports.py` 新增坐标读取 port，例如 `PointerPositionReader.current_position() -> Point`。
- [x] 2.2 在 `core/ports.py` 新增按键状态 port，例如 `KeyStateReader.is_pressed(key: str) -> bool`。
- [x] 2.3 新增真实坐标读取 adapter，使用 `pyautogui.position()` 转换为 `Point`。
- [x] 2.4 新增真实终端按键状态读取 adapter，并在终端不可交互或运行环境不可用时报告清晰 setup 错误。
- [x] 2.5 新增独立命令入口 `game-coordinate-recorder`，不挂到现有 demo CLI 参数中。
- [x] 2.6 更新项目依赖元数据，确认第一版不引入全局键盘监听依赖。
- [x] 2.7 将平台 adapter 按边界整理为 `adapters/desktop/` 和 `adapters/macos/`，保持工具核心与平台实现分离。

## 3. 测试与文档

- [x] 3.1 添加单元测试，覆盖每秒打印与 50ms 按键检测互不阻塞。
- [x] 3.2 添加单元测试，覆盖长按 `1` 不重复记录。
- [x] 3.3 添加单元测试，覆盖按 `1` 时会重新读取最新坐标，按 `Q/q` 时会在按键检测循环中快速退出。
- [x] 3.4 添加单元测试，验证工具通过坐标读取 port 获取坐标，而不是直接调用平台库。
- [x] 3.5 添加单元测试，验证工具不会创建或执行脚本动作，也不会新增获取坐标 action。
- [x] 3.6 添加 CLI/依赖适配测试，覆盖 setup 错误包装。
- [x] 3.7 更新 README，说明坐标记录工具的运行方式、权限要求、当前记录的是屏幕绝对坐标，以及默认 1 秒显示/50ms 按键检测节奏。
- [x] 3.8 运行测试套件、OpenSpec change 校验和 diff hygiene 检查。
