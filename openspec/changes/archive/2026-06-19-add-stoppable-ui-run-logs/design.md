## Context

当前本地 UI 的 `/api/run-script` 会在 HTTP 请求线程内同步调用 application 层运行脚本。短脚本可用，但持续轮询脚本会让请求长期不返回，页面也没有停止入口。图片匹配路径通过 `ScreenImageLocator` 完成，但没有耗时日志，用户无法判断图片识别慢在哪里。

项目约束是 ports-and-adapters：取消和日志属于执行规则/application 可注入能力；HTTP 只做请求转换；真实截图和图像匹配仍停留在平台 adapter。

## Goals / Non-Goals

**Goals:**

- UI 可以启动一个后台脚本运行，并通过停止按钮取消当前运行。
- UI 可以轮询运行状态，并看到标准输出、错误输出和图片匹配耗时日志。
- `ScriptRunner` 在循环、条件分支、等待和图片定位路径上能检查取消信号。
- 图片查询路径能记录模板、耗时、是否命中和置信度。

**Non-Goals:**

- 不为 CLI 增加后台任务管理；CLI 仍通过前台运行和 `Ctrl+C` 停止。
- 不实现多任务并发队列；第一版 UI 同一时间最多一个脚本运行。
- 不优化 OpenCV 算法本身；本次只暴露耗时诊断。

## Decisions

1. 在 engine 层引入可选 `CancellationToken` 协议和 `RunLogger` 协议。
   - 原因：runner 可以保持平台无关，通过注入检查取消和写日志。
   - 备选：只在 UI 线程层面停止。缺点是无法让正在解释的脚本有序退出，也无法在核心路径记录图片匹配耗时。

2. application 层管理一个 `ScriptRunSession`，由后台线程执行脚本。
   - 原因：HTTP handler 保持薄，只调用 start/status/stop 用例；长脚本不会占住浏览器请求。
   - 备选：浏览器端 `AbortController` 取消 fetch。缺点是只能断开请求，不能可靠停止后端脚本。

3. 第一版同一时间只允许一个 UI 脚本运行。
   - 原因：当前项目目标是本机游戏自动化，多脚本并发会争用鼠标、屏幕和截图权限。
   - 备选：多会话并发。缺点是会增加设备互斥和 UI 状态复杂度。

4. 图片匹配日志在 portable 查询层记录，不在平台 adapter 中打印。
   - 原因：查询层知道模板、region、置信度和最终结果，且可在 dry-run/fake 下测试；adapter 仍只实现端口。

## Risks / Trade-offs

- 正在执行的真实 `InputDevice.wait()` 或一次图像匹配调用不可被中途打断 → 在调用前后检查取消，最长延迟取决于单次 wait 或单次截图匹配耗时。
- 后台线程共享 stdout 捕获可能影响测试或并发请求 → UI 后台运行使用 session 级日志 sink；保留原同步 `run_named_script` 路径兼容现有测试。
- UI 状态轮询会增加少量 HTTP 请求 → 使用简单定时轮询，避免引入 WebSocket 或 SSE 的复杂度。
