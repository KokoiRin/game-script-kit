## Context

当前 Star 已经有 `screen-state-probe` 能力，可以从 `assets/screen-states.json` 读取状态候选并识别当前界面。脚本引擎已有 `ColorIs` 和 `ImageExists` 条件，但它们表达的是底层屏幕信号；用户真正想写的是“如果当前是主页，就点头像”这类状态驱动逻辑。

## Goals / Non-Goals

**Goals:**
- 让脚本模型可以表达当前界面状态判断。
- 保持 engine 通过 port 获取状态，不知道 UI、配置文件或平台 adapter。
- 让本地控制 application 能把现有状态探测能力注入脚本运行。
- 提供一个简单示例脚本，证明状态条件可用于分支。

**Non-Goals:**
- 不在本轮引入变量、赋值或自然语言编译前端。
- 不让脚本直接读取 `screen-states.json`。
- 不做状态缓存；每次条件评估先按现有状态探测执行一轮。
- 不改变现有 `ImageExists` / `ImageTarget` 语义。

## Decisions

1. **领域层新增 `ScreenStateIs` 条件。**
   条件只保存期望状态名称和最低置信度，不关心状态如何识别。这样脚本可以写出用户可理解的业务状态，同时领域层保持纯模型。

2. **engine 新增 `ScreenStateReader` port。**
   `condition_evaluator` 收到 `ScreenStateIs` 后调用 port 读取当前状态。缺少 port 时抛出运行时错误，和现有颜色/图片条件保持一致。

3. **本地控制 application 负责包装状态探测。**
   `LocalControlApplication` 已经知道项目根目录、状态配置、图像定位 adapter 和日志；它可以创建一个 reader，把 `probe_screen_state_once` 的结果转换成当前状态字符串。

4. **dry-run 先使用固定状态 reader。**
   `run_script` 增加 `dry_run_screen_state` 参数。需要状态 reader 的 dry-run 脚本使用固定状态，便于可重复测试和 demo。

## Risks / Trade-offs

- [Risk] 每次状态条件都会触发一轮截图和匹配，复杂脚本可能变慢。→ Mitigation: 第一版保持语义简单，后续再做状态缓存或一轮内复用。
- [Risk] 状态名称拼错会导致条件永远为假。→ Mitigation: 后续可加入配置校验和 UI 状态选择；本轮先保持字符串模型。
- [Risk] CLI 直接运行真实状态脚本时没有项目配置上下文。→ Mitigation: 本轮优先保证本地控制 application 路径可注入真实状态 reader，dry-run 和测试路径可验证。
