## 1. 项目初始化

- [x] 1.1 为游戏自动化框架创建最小 Python package 结构。
- [x] 1.2 为选定的 macOS 鼠标指针自动化后端和测试运行器添加项目依赖元数据。
- [x] 1.3 添加简短 README 或 demo 说明，记录 macOS 权限要求和坐标假设。

## 2. 输入设备契约

- [x] 2.1 定义平台无关的数据类型，用于表示屏幕坐标、鼠标按钮和指针动作时序。
- [x] 2.2 定义包含移动、点击和拖动操作的输入设备接口。
- [x] 2.3 添加 adapter 级错误类型，用于表达缺少依赖、缺少权限或环境不支持。

## 3. 核心 Workflow

- [x] 3.1 实现一个 demo 游戏 workflow，接收注入的输入设备实现。
- [x] 3.2 确保 core workflow 模块不会导入 macOS 专用 adapter 模块。
- [x] 3.3 为测试提供 fake 输入设备，用于记录 workflow 请求的鼠标指针操作。

## 4. macOS Adapter

- [x] 4.1 在输入设备接口背后实现 macOS Python 鼠标指针 adapter。
- [x] 4.2 将移动、点击和拖动请求转换为选定 macOS 自动化后端的调用。
- [x] 4.3 当依赖或权限不可用时，暴露清晰的 adapter 级 setup 错误。

## 5. Demo 入口

- [x] 5.1 添加可运行的 demo 命令或脚本，把 demo workflow 接到 macOS adapter。
- [x] 5.2 添加 dry-run 或测试模式，让同一个 workflow 可以连接 fake 输入设备运行。
- [x] 5.3 将平台选择和 adapter 构造保留在业务 workflow 代码之外。

## 6. 验证

- [x] 6.1 添加测试，证明 demo workflow 使用 fake 输入设备时会记录预期的操作顺序。
- [x] 6.2 添加测试，证明导入 core workflow 代码不会导入或初始化 macOS adapter。
- [x] 6.3 使用 mocked backend calls 添加聚焦 adapter 测试，覆盖移动、点击、拖动和 setup 错误。
- [x] 6.4 运行测试套件和该变更的 OpenSpec 校验。
