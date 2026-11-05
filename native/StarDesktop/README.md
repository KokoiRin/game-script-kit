# Star macOS 原生壳

使用 macOS 13+ 的 SwiftUI 和 AppKit，SwiftPM 不包含任何第三方 UI 包。
Python 核心运行在受壳管理的独立进程中；不启动浏览器或本地 Web 服务。

## 开发环境

在 Mac 安装 Xcode 或 Command Line Tools（Swift 5.9+），然后在仓库根目录准备 Python：

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
swift build --package-path native/StarDesktop
mkdir -p ~/StarWorkspaces/my-tasks
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks ui
```

也可使用 `.venv/bin/star-desktop`，首次在原生目录选择器选择任务根。需要进入
运行页时可使用 `star-desktop --workspace PATH --tab run`。
当前工作区下的 `.star/desktop.log` 保存后台与会话诊断。

## Finder 应用

在仓库根目录执行：

```bash
.venv/bin/python tools/build_macos_app.py
open native/StarDesktop/dist/Star.app
```

开发版 Info.plist 绑定构建时的仓库路径和 Python 解释器；移动仓库或重建环境后
重新构建应用。当前未打包 Python、进行签名或公证，不能当作独立发行版。
也可用 `STAR_PYTHON`、`STAR_SOURCE_ROOT` 指定开发环境。

## 职责

- `Main.swift`：原生窗口、菜单、工作区选择与统一退出路径。
- `Session.swift`：后台监督、请求超时、管道与日志回收、单帧缓存。
- `WorkspaceView.swift`：素材准备与脚本运行界面。
- `Canvas.swift`：原生截图画布、像素取点及框选，不解释脚本。
- Python `desktop_backend.py`：串行协议分发、后台执行会话、文件锁与临时 PNG。

运行中禁止截取新画面或重复启动脚本。关闭时先请求取消、等待线程结束；平台
调用无响应才使用有界的进程回收，不重放动作。详细边界见 [ADR 0008](../../docs/adr/0008-native-macos-desktop.md)。

## 验收

云端已验证 Python 部分与 Swift 语法，尚未用 macOS SDK 构建或验收 GUI。
`.github/workflows/macos-native.yml` 包含 Mac 构建检查，需在推送后实际运行。
回到 Mac 后先构建，再检查工作区切换、取点和裁图、模拟运行、运行中关闭窗口、
Command+Q、后台意外退出，以及辅助功能和屏幕录制权限。授权对象以系统弹窗为准。
