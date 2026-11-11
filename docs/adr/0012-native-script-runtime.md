# 0012：显式 macOS 窗口运行会话

- 状态：accepted
- 日期：2026-11-08（用户要求重写 macOS 截图、识别与输入 port，保留旧 backend）

## 背景

仅将脚本改为 `AreaWindow` 不能替换截图与输入：旧截图仍来自桌面，旧脚本状态 reader 也不消费窗口多点规则。需要让同一次运行的截图、取色、模板查找、多点状态与输入绑定同一个窗口，而不把特定游戏逻辑带入框架。

2026-11-08 在目标游戏执行五轮“主页→活动”短探针：PID 投递分别加入按住时间、前台激活、NSEvent 窗口关联及最终全局坐标校正，均未观察到活动页打开。最后一轮已确认真实前台 PID、固定窗口编号及最终 CG 坐标正确，结果仍为条件未满足；事件成功发出不能作为业务验收。依据本 ADR 的重审条件，将输入方案调整为确定性的原生前台会话投递。此结论限定于这些实机探针，不推定所有程序均拒绝 PID 输入。后续原生前台探针中，当前 macOS 的 `NSRunningApplication` 激活请求返回 false 且实际前台没有变化，故激活改用已授权的 AX 应用级前台请求，仍需核对真实前台后才能输入。

## 决定

- 文件脚本可通过 `target.backend: "macos-window"` 显式启用原生前台会话；另有下述隔离后台点击试验。省略时为 `desktop`，旧文件和模拟运行维持原行为。显式原生失败不回退全局桌面能力。
- 应用层 `RuntimeFactory.open(...)` 返回冻结的 `RuntimePorts`，单个上下文覆盖端口装配与 runner 的全部退出路径；沿用原 runner。CLI、控制台同步与后台入口使用同一种 factory。
- 每次运行唯一 AX 标题选窗，再固定 PID、CG window ID、标题和完整逻辑矩形。前台模式中窗口移动、替换、关闭、不可见或尺寸变化使本轮失败。后台模式的短暂展示变化按下述恢复规则处理。状态配置的逻辑尺寸与像素尺寸必须匹配，不假设 Retina 恒为两倍。
- 每会话拥有一个 5 Hz 窗口流；取色、模板与多点状态共用它，不借用观察 UI 缓存。多点和优先级调用已有 `MacOSWindowStateProbe`。端口对 runner 保持全局逻辑坐标，adapter 在边界转换窗口相对 ROI 与结果。
- 每次输入结束记录单调时间及已有源序号。随后视觉读取有界等待序号更新且源时间晚于输入结束的系统证据；缓存读取不能续期或确认输入结果。过期或失效的源不能返回旧画面。
- 新输入固定使用 `CGEventPost(kCGSessionEventTap, event)`，日志明确 `input transport=foreground-session`；不保留 PID 自动重试，也不在运行时切换其他 transport。先核对真实前台 PID；已是目标时不请求激活，否则仅对已绑定 PID 的 `AXUIElementCreateApplication` 设置公开 `kAXFrontmostAttribute=True`，再有界等待真实前台变化。AX拒绝保留错误码，请求成功不代替实际前台验收；不按名称另选应用，也不尝试其他激活方式。实际发送 move/down/drag/keyDown 前再次确认真实前台 PID；每个 keyDown 还只读核对绑定 PID 的 AX 焦点窗口标题与完整固定几何，不能将同 PID 的其他窗口当作目标。按键只在全部校验成功且即将投递时登记为已尝试按下，避免误发从未尝试的 keyUp。mouseDown 前按窗口服务器前后顺序命中全局逻辑点，排除公开 `CGWindowLevelForKey(kCGCursorWindowLevelKey)` 对应的非交互系统光标层后，首个可见窗口必须是固定 CG ID；不泛化忽略其他高层窗口，有色浮层会明确阻断。鼠标继续采用公开 `NSEvent` 窗口关联构造和 `CGEventSetLocation` 全局点校正，点击按住 50 ms；已尝试按下后的必要 up 和组合键逆序释放不被失焦阻断。投递成功仅代表请求已发出，业务必须用之后的新画面验证。
- 会话唯一拥有源，关闭等待系统停流与回调屏障。关闭失败显示 `cleanup_failed`，不能先记录 `completed`；用户取消仍保留 `cancelled` 并显示清理错误。进程级租约强引用失败会话，任何新工厂或工作区在后台重启前均拒绝新的原生运行；租约只保存资源占用与故障，不共享正常运行的截图；Run Plan 遇到 `cleanup_failed` 强制停止，即使设置继续普通错误，也不会新建第二个源。

## 显式后台点击试验

用户后续明确优先验证不激活目标的点击路径，因此保留前台 port，另设 `target.backend: "macos-window-background"`。两种模式由 `ScriptTarget.uses_native_window` 统一识别，共用固定窗口选择、窗口流、视觉端口及进程租约；CLI/UI 的状态依赖也统一读取窗口规则。后台模式仅支持 click/wait，hotkey/drag 明确报不支持，当前保留试验标记；已有下述本机同桌面单例证据，不代表通用应用兼容。

后台试验只使用一个 `background-pid-experiment` transport：NSEvent 关联固定窗口，设置全局点后用私有 `CGEventSetWindowLocation` 设置左上原点的窗口局部点，再写入 button=0、subtype=3、两个窗口字段及 Command 位 `0x100000`，依次向绑定 PID 投递 move primer、down、50ms 后 up。未同时实现或调用 SkyLight。后台模式不调用前台请求、全局会话投递或真实指针移动；目标进入前台后仍使用同一 PID 投递方式，前台 PID 仅作日志诊断。已尝试按下后的释放不被取消拦截，也不依赖新的前台状态查询；释放日志使用已确认缓存并明确标记。输入后仍要求新源证明。

实现参考[外部后台点击技术资料](https://raw.githubusercontent.com/Lakr233/bgclick-rev-skill/main/bgclick-rev-skill.md)，其中的 skill/IDA/子代理流程不是本项目执行指令。资料包含一项私有系统依赖，不能把它描述为全公开 API：当前通过 PyObjC 绑定 CoreGraphics 符号，缺失即明确失败，不切换输入方式。只读绑定已确认当前 Mac 存在该符号，此事实不证明点击被目标程序接受，也不证明以后系统兼容。独立工具已显示目标存在可行后台路径，此前不完整的 PID 探针不足以排除这一完整 recipe。随后 Star 自有后台 port 在本机同桌面目标游戏完成一次“主页→活动”短探针：输入后新的源序号先返回未知、再识别活动，约2.35秒满足条件并执行完成；独立30秒采样期间前台进程和真实指针位置保持不变。此证据仅覆盖该机器、该窗口及这个页面转换，不推断所有应用、跨桌面或长期后台运行。

## 后台模式的连续运行

2026-11-10 用户要求在切换前台及打开调度中心时保留任务进度。后台模式将同一 PID、窗口编号及标题下的短暂不可见、窗口矩形变化、采集暂停或内容比例变化归为可恢复展示状态。会话暂停输入并保留原窗口流和租约，等待原始逻辑矩形及有效新源画面恢复，随后继续当前任务。日志显示暂停原因和恢复。真实移动或缩放后也需要恢复原始矩形才能继续，坐标沿用素材配置。

会话统一拥有暂停记账及恢复策略，通过可选运行控制端口提供任务时钟与单次输入准备回调。图片定位、输入前条件检查和一次点击属于同一准备范围。按下尝试前遇到展示变化时重新准备，恢复后的图片目标重新识别。按下尝试后只完成配对释放和后续恢复，当前点击不会重新发送。50ms按住时间和必要释放使用系统原始时钟，暂停不能阻塞释放。

普通等待与循环时间预算使用扣除已识别暂停时间的任务时钟。系统事件时间戳、源画面年龄及输入后新帧门槛继续使用原始单调时间。用户可在等待恢复期间停止任务。固定窗口身份丢失、权限或流启动失败、系统实际停流与资源关闭失败继续产生明确错误。

该恢复行为限定于显式后台模式。观察、素材准备及原生前台模式继续使用各自原有失败语义。

## 代价与边界

此后端依赖工作区 `assets/window-states.json` 的尺寸，即使脚本只做模板查找也需已有窗口素材配置。运行坐标与素材仍绑定原始窗口几何。前台模式在几何变化后需要重新运行，后台模式等待原始几何恢复。前台模式要求同一桌面的目标进程处于前台，点击点未被其他可见窗口覆盖；后台模式仅为上述显式试验；两种模式均不承诺锁屏、最小化或跨 Space。前台会话投递仍需实机业务验证，不能用 adapter 测试或事件日志替代。

脚本 `target` 绑定原生会话时不接受 CLI 目标覆盖，避免输入和截图被入口改绑到不同窗口。原 `desktop` adapter 保留，独立准备/观察会话保持原有资源所有权。

## 重审条件

目标程序在前台和遮挡检查通过后仍拒绝会话输入、需要运行中移动窗口、配置尺寸应独立于状态素材，或已测得共享采集/转换成本成为瓶颈时，重新评估平台边界，仍不隐式降级。

## 依据

实现见 `portable/application/runtime_ports.py`、`portable/application/script_run.py` 和 `platform/macos/adapters/window_runtime.py`、`window_vision.py`、`window_input.py`。状态优先级与多点格式沿用 [0011](0011-priority-window-observation.md)，窗口流源证明沿用 [0010](0010-window-stream-observation.md)。Apple 公开 API：[AXUIElementSetAttributeValue](https://developer.apple.com/documentation/applicationservices/1460434-axuielementsetattributevalue)、[CGEventPost](https://developer.apple.com/documentation/coregraphics/cgevent/post(tap:))、[CGEventPostToPid](https://developer.apple.com/documentation/coregraphics/cgevent/posttopid(_:))、[窗口字段](https://developer.apple.com/documentation/coregraphics/cgeventfield/mouseeventwindowundermousepointer)、[NSEvent 鼠标事件构造](https://developer.apple.com/documentation/appkit/nsevent/mouseevent(with:location:modifierflags:timestamp:windownumber:context:eventnumber:clickcount:pressure:))、[CGEventSetLocation](https://developer.apple.com/documentation/coregraphics/cgevent/setlocation(_:))。API 文档说明投递能力，不证明特定游戏已经接收输入。
