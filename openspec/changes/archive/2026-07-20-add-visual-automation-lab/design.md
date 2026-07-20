## Context

Star 已经有 dry-run、fake adapter 和大量纯行为测试，但图像定位、真实鼠标和浏览器状态变化仍依赖外部游戏窗口。真实应用会升级、消失或产生副作用，因此不能成为稳定的开发基准。靶场需要同时提供可见像素界面和独立真值通道：Star 只消费前者，测试程序只用后者验收。

## Goals / Non-Goals

**Goals:**

- 用独立进程提供可重复的本地目标应用。
- 第一版覆盖图片目标、加载等待、确认动作和完成状态。
- 由服务端状态机保存真值和事件，页面只负责渲染和提交用户点击。
- 不增加第三方运行依赖，并能通过 pytest 验证状态机与 HTTP contract。

**Non-Goals:**

- 不制作通用场景编辑器。
- 不把靶场逻辑放进 `game_automation.portable`。
- 不让 Star 脚本通过靶场 API 执行动作或读取状态。
- 不在第一版实现录屏、OCR、多窗口或 CI 中的真实桌面点击。

## Decisions

### 独立 package 和入口

新增顶层 `star_visual_lab` package 和独立 `star-lab` console script。它与 `game_automation` 共享安装环境，但不导入 Star 的 domain、application 或 platform 模块，避免测试目标和被测系统耦合。

未采用 `star lab` 子命令，因为现有 `star` CLI 已承担较多用户入口职责，靶场属于开发辅助目标应用，不应扩大其分支和依赖。

### Python 标准库 HTTP 服务与原生前端

使用 `ThreadingHTTPServer`、静态 HTML/CSS/JavaScript，不引入 React、Electron 或新的包管理链。浏览器仍会产生真实窗口和像素，足以验证屏幕识别与鼠标操作。

### 服务端状态机是真值来源

`TaskFlowScenario` 保存 `home -> task_list -> loading -> confirm -> completed` 状态和事件序列。页面通过 `/api/action` 请求合法转换，通过 `/api/state` 轮询渲染。加载完成由单调时钟驱动，状态读取时刷新到期转换，测试可注入时钟。

### 视觉通道与验收通道分离

Star 后续只能通过屏幕截图和输入设备操作页面；验收代码通过 `/api/state` 和 `/api/events` 判断结果。HTTP 动作接口属于目标应用自身的按钮处理协议，不提供给 Star 脚本直接调用。

### 第一版故障模式

- `normal`：目标存在，使用短加载延迟。
- `slow`：目标存在，使用更长加载延迟。
- `missing_target`：任务列表不展示目标，也不接受选择目标动作。

模式和延迟只能通过启动参数或 `/api/reset` 配置，确保每次验证可重复。

## Risks / Trade-offs

- [浏览器缩放和 Retina 像素可能影响模板匹配] → 靶场使用固定尺寸、无动画的高对比目标；真实 smoke 仍记录当前设备缩放。
- [HTTP 测试只能证明靶场本身正确] → 保留真实屏幕 smoke 流程，后续 Star 能力必须同时通过 fake 测试和至少一次本机 smoke。
- [靶场逐渐变成第二套产品 UI] → 第一版只允许固定场景和故障参数，不增加可视编辑器。

## Migration Plan

新增能力不迁移现有配置。若出现问题，可移除 `star-lab` 入口和 `star_visual_lab` package，不影响现有 `star` 命令与脚本。

## Open Questions

无。第一版先验证固定任务流是否足以承载后续 Star 端到端开发。
