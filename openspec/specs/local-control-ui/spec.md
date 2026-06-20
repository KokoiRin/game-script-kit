# local-control-ui Specification

## Purpose
定义本地控制 UI 的启动、脚本运行、固定测试任务和分层约束，确保窗口入口复用 application 层能力而不穿透到 engine 或平台 adapter。
## Requirements
### Requirement: 本地 UI 可启动

系统 SHALL 提供 `star ui` 子命令启动本地控制 UI 服务，并默认打开本机浏览器窗口访问该服务。

#### Scenario: 启动本地 UI

- **WHEN** 用户运行 `star ui`
- **THEN** 系统启动本地 HTTP UI 服务并打开浏览器窗口

#### Scenario: 测试模式启动本地 UI

- **WHEN** 用户运行 `star ui --no-open`
- **THEN** 系统启动本地 HTTP UI 服务但不打开浏览器窗口

### Requirement: UI 列出命名脚本

系统 SHALL 在 UI 中展示当前脚本 catalog 里的脚本名称。

#### Scenario: 页面加载脚本列表

- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面可获取并展示所有已注册脚本名称

### Requirement: UI 运行命名脚本

系统 SHALL 允许用户从 UI 选择脚本，并以 dry-run 或真实模式运行该脚本。

#### Scenario: dry-run 运行脚本

- **WHEN** 用户选择脚本、选择 dry-run 模式并点击运行
- **THEN** 系统通过 application 层运行该脚本并在 UI 中展示退出码和运行输出

#### Scenario: dry-run 使用指定颜色

- **WHEN** 用户输入 `#RRGGBB` dry-run 颜色并运行颜色条件脚本
- **THEN** 系统使用该固定颜色评估颜色条件

#### Scenario: dry-run 使用指定界面状态

- **WHEN** 用户输入 dry-run 模拟状态并运行界面状态条件脚本
- **THEN** 系统使用该固定状态评估界面状态条件

#### Scenario: 脚本运行失败

- **WHEN** 脚本运行返回非零退出码或错误消息
- **THEN** UI 展示非零退出码和错误消息

### Requirement: UI 运行图片点击

系统 SHALL 允许用户把模板图片放入项目 `assets/` 目录，并从 UI 选择该图片执行一次查找并点击动作。UI MUST 只把图片资源名称交给 application 层，由 application 层校验资源路径、构造脚本并归一化运行结果。

#### Scenario: UI 列出图片资源

- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面可获取并展示 `assets/` 目录中的支持图片文件

#### Scenario: UI dry-run 图片点击

- **WHEN** 用户选择一张图片、选择 dry-run 模式并点击“查找并点击图片”
- **THEN** 系统通过 application 层构造图片目标点击脚本，使用该图片作为 dry-run 命中模板，并展示计划点击输出

#### Scenario: UI 真实图片点击

- **WHEN** 用户选择一张图片、取消 dry-run 模式并点击“查找并点击图片”
- **THEN** 系统通过 application 层构造图片目标点击脚本，并使用真实桌面图像定位 adapter 查找该图片后点击匹配中心点

#### Scenario: UI 拒绝非法图片资源

- **WHEN** UI 请求使用不存在、后缀不支持或不在 `assets/` 目录内的图片资源
- **THEN** 系统返回配置错误并且不执行图片点击脚本

### Requirement: UI 运行固定测试任务

系统 SHALL 提供固定测试按钮运行项目白名单测试命令，并展示测试结果；系统 MUST NOT 接受用户输入任意 shell 命令。

#### Scenario: 运行全部测试

- **WHEN** 用户点击“运行测试”
- **THEN** 系统运行白名单中的全部测试命令并展示退出码、标准输出和标准错误

#### Scenario: 拒绝未知测试任务

- **WHEN** UI 请求运行白名单之外的测试任务
- **THEN** 系统返回配置错误并且不执行外部命令

### Requirement: UI 保持分层职责

系统 SHALL 把 UI 实现限制在入口 adapter 和 application 层；UI MUST NOT 直接解释脚本步骤、直接创建 `ScriptRunner`，或直接导入平台自动化 adapter。

#### Scenario: UI 通过 application 层运行脚本

- **WHEN** UI 收到运行脚本请求
- **THEN** 它调用 application 层用例完成 catalog 查找、运行配置和结果归一化

#### Scenario: Recorder 不进入第一版 UI

- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面不提供坐标记录器控制入口，坐标记录器继续通过 `star recorder` 使用

### Requirement: UI 图片点击支持最低匹配置信度

本地控制 UI SHALL allow image-click requests to provide a minimum match
confidence, so real image clicks can use OpenCV fuzzy matching instead of exact
pixel matching.

#### Scenario: HTTP 图片点击请求传递最低置信度
- **WHEN** 浏览器调用 `/api/click-image` 并提供 `min_confidence`
- **THEN** HTTP adapter 会把该值传给 application 层图片点击用例

#### Scenario: application 用最低置信度构造图片目标
- **WHEN** application 层运行图片点击用例
- **THEN** 它使用请求中的最低置信度构造 `ImageTarget`

#### Scenario: 非法最低置信度
- **WHEN** 图片点击请求提供小于等于 0 或大于 1 的最低置信度
- **THEN** application 层拒绝请求并返回配置错误

### Requirement: UI 支持停止后台脚本运行
本地控制 UI SHALL 以后台运行会话启动命名脚本，并允许用户停止当前运行中的脚本。系统 MUST 保持同一时间最多一个 UI 脚本运行，且 HTTP adapter MUST 只把启动、查询和停止请求委托给 application 层。

#### Scenario: 启动后台脚本
- **WHEN** 用户在 UI 中点击运行脚本
- **THEN** 系统启动一个后台脚本运行会话，并立即返回该会话的运行中状态

#### Scenario: 查询运行状态
- **WHEN** 页面轮询运行状态接口
- **THEN** 系统返回当前会话是否运行中、最近退出码以及已收集日志

#### Scenario: 停止运行中脚本
- **WHEN** 用户点击停止按钮且脚本仍在运行
- **THEN** 系统请求取消当前运行会话，并最终返回取消后的非零退出结果

#### Scenario: 拒绝重复启动
- **WHEN** 已有 UI 脚本会话仍在运行时用户再次请求运行脚本
- **THEN** 系统返回运行中错误，并且不会启动第二个脚本

### Requirement: UI 展示运行日志和图片匹配耗时
本地控制 UI SHALL 展示后台脚本运行期间产生的日志，包括普通输出、错误输出和图片匹配耗时诊断。

#### Scenario: 展示图片匹配日志
- **WHEN** 脚本执行图片存在判断或图片目标点击
- **THEN** UI 日志包含该次图片匹配的模板路径、耗时毫秒、是否命中和置信度摘要

#### Scenario: 日志随状态轮询更新
- **WHEN** 后台脚本仍在运行且产生新日志
- **THEN** 页面下一次状态轮询展示追加后的日志内容

### Requirement: UI 提供界面状态探测 tab
本地控制 UI SHALL 提供独立的界面状态探测 tab，让用户在不运行脚本的情况下持续观察当前界面状态。HTTP adapter MUST 只把探测启动、停止和状态查询请求委托给 application 层。

#### Scenario: 页面展示界面探测入口
- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示界面状态探测 tab、启动探测按钮、停止探测按钮和探测日志区域

#### Scenario: 启动界面状态探测
- **WHEN** 用户点击启动界面状态探测
- **THEN** UI 调用探测启动接口，并展示探测会话运行中状态

#### Scenario: 查询界面状态探测
- **WHEN** 页面轮询探测状态接口
- **THEN** UI 展示当前识别状态、最近退出码以及已收集日志

#### Scenario: 停止界面状态探测
- **WHEN** 用户点击停止界面状态探测
- **THEN** UI 调用探测停止接口，并最终展示探测会话已停止状态

### Requirement: UI 生成状态区域诊断截图
本地控制 UI SHALL 提供状态区域诊断入口，根据当前屏幕截图和 `assets/screen-states.json` 中的命名区域生成带区域框的诊断图片。HTTP adapter MUST 只把请求委托给 application 层，UI MUST 展示退出码、输出信息和诊断图片。

#### Scenario: 页面展示区域诊断入口
- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示用于生成状态区域诊断截图的按钮

#### Scenario: 生成并展示区域诊断截图
- **WHEN** 用户点击区域诊断按钮且 `assets/screen-states.json` 包含命名区域
- **THEN** 系统保存一张带区域框和区域名称的诊断图片
- **AND** UI 在诊断预览区域展示该图片

#### Scenario: 缺少状态区域配置
- **WHEN** 用户点击区域诊断按钮但状态配置不存在、非法或没有命名区域
- **THEN** 系统返回非零退出码和清晰错误消息
- **AND** 系统不启动界面状态探测循环

### Requirement: UI dry-run 支持指定当前界面状态
本地控制 UI SHALL 允许用户在运行命名脚本时指定 dry-run 当前界面状态。HTTP adapter MUST 把该值传给 application 层脚本运行用例；application 层 MUST 用该值作为 `ScreenStateIs` 条件的 dry-run 状态来源。

#### Scenario: 页面展示模拟状态输入
- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示用于 dry-run 的模拟界面状态输入
- **AND** 该输入默认值为 `未知`

#### Scenario: dry-run 状态条件脚本使用模拟状态
- **WHEN** 用户在 UI 中输入模拟状态 `主页`
- **AND** 用户以 dry-run 模式运行包含 `ScreenStateIs("主页")` 的脚本
- **THEN** 系统通过 application 层使用 `主页` 作为 dry-run 当前状态
- **AND** 脚本按状态条件命中路径执行
