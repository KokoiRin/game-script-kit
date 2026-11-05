# 0008：macOS 原生壳与受管理的 Python 后台

- 状态：accepted
- 日期：2026-11-05（用户选择优先 macOS 原生，暂不要求 Windows 界面）
- 性质：桌面技术栈、进程生命周期与性能边界；替换网页 UI 入口

## 背景

用户明确不希望继续用网页调试界面，希望桌面应用管理好生命周期并逐步扩展。
在比较 Qt 的跨平台便利与依赖体积后，用户选择 macOS 原生优先，同时关注性能。
已有准备与执行用例可继续使用，不应因更换 UI 改写脚本规则。

## 决定

- 界面使用系统 SwiftUI；AppKit 提供截图画布、菜单、窗口和应用退出生命周期。
  不依赖 Qt、Electron、WebView 或常驻 HTTP 服务。最低 macOS 13，使用 SwiftPM 构建。
- 保留 Python 的脚本执行、状态识别、素材准备与平台适配。原生壳监督一个独立
  Python 后台，通过标准输入输出的 JSON-RPC 行协议通信。
- 每个后台固定绑定一个显式工作区，用内核文件锁阻止同一工作区的重复后台。
  切换工作区先结束旧后台再启动新后台，不复用旧帧或运行状态。
- `star ui`、`star prepare` 与 `star-desktop` 都进入原生壳。没有工作区时由原生目录
  选择器选择；`prepare` 保持要求显式工作区。旧 host/port/no-open 参数与网页 UI 源码移除。

## 生命周期

原生会话有 idle、starting、ready、stopping、failed 阶段。界面不执行识图、截图或脚本。
启动先校验协议版本，后台异常退出显示诊断，手动重启，不重放上一次操作。

关闭窗口、Command+Q、终端中断均请求统一退出：发送 shutdown、关闭输入管道、
后台请求取消并等待实际线程退出，随后清理冻结帧临时目录并释放工作区锁。
管道 EOF 也走相同回收路径。固定真实等待每最多 50ms 检查取消；原子平台调用
仍可能阻塞，不能声称所有操作都可立即中止。

宿主在 7 秒后仍未观察到后台退出时发送 SIGTERM，再等 2 秒后才回收该后台进程组；
仅对已握手确认属于该后台的进程组发送信号。强制回收会记录诊断，最后一次业务
操作必须独立核对。后台请求超时也先回收会话，不自动重试或启动第二个执行进程。

## 性能与数据

- 截图作为 PNG 写入后台独占临时目录，协议只交付帧 ID、路径及尺寸，不传 Base64。
  新帧删除旧文件，壳只持有当前 NSImage，读取图片文件在后台任务中完成。
- 原生画布仅在帧或框选变化时重绘，脚本状态每 500ms 查询一次，不以 UI 刷新驱动截图。
- 运行会话 stdout/stderr 各保留最多 262144 字符、最近 2048 个事件；事件字段最多
  4096 字符，跨进程每次仅发送最多 65536 字符 stdout 和 8192 字符 stderr。
- 原生日志面板限制在 32768 字符，诊断文件约 1MiB 时重置。长期运行不无限缓存事件、帧或日志。
- 协议输出使用启动时保存的原始流，避免运行线程的全局 stdout 重定向吞掉响应。

## 当前范围与验证限制

准备和运行使用同一壳，但准备用例、执行用例仍互相独立。运行时禁止新的素材
操作或重复启动，停止可独立请求。准备选窗不会隐式更改脚本执行目标；CLI 的
显式目标窗口参数继续可用。持续采集、实时状态流和动作结果驱动仍未实现。

当前 `.app` 是开发构建，绑定本机 checkout 和 `.venv`，没有打包 Python、签名、公证
或宣称可直接分发。核心的 Python、OpenCV 等依赖仍存在，原生 UI 无第三方库依赖。

Linux 可验证协议、子进程 EOF、单实例锁、等待取消、缓存与内核回归；Swift 源码
语法解析不能代替 SDK 类型检查。已加入 macOS CI 构建配置，当前会话未运行该 CI，
原生应用编译、窗口交互、系统权限、正常退出与平台卡住后的回收需在 Mac 验收。

## 依据

- [原生会话](../../native/StarDesktop/Sources/StarDesktop/Session.swift)、[应用入口](../../native/StarDesktop/Sources/StarDesktop/Main.swift)。
- [后台协议](../../src/game_automation/platform/local_desktop/entrypoints/desktop_backend.py)、[启动器](../../src/game_automation/platform/local_desktop/entrypoints/desktop_app.py)。
- [构建说明](../../native/StarDesktop/README.md)、[进程测试](../../tests/test_desktop_backend.py)。
