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

本地控制 UI SHALL 提供独立的界面状态探测 tab，让用户在不运行脚本的情况下持续观察当前界面状态。HTTP adapter MUST 只把探测启动、停止和状态查询请求委托给 application 层。界面状态候选展示 MUST 包含候选状态、耗时、命中置信度、最佳匹配置信度和最佳匹配位置。

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

#### Scenario: 展示候选最佳置信度

- **WHEN** 页面轮询 `/api/screen-state-probe` 且候选结果包含 `best_confidence`
- **THEN** HTTP JSON 的候选 object 包含 `best_confidence`
- **AND** UI 候选列表展示该候选的最佳置信度
- **AND** 未命中候选的命中置信度可以为 `null`

#### Scenario: 展示候选最佳位置

- **WHEN** 页面轮询 `/api/screen-state-probe` 且候选结果包含 `best_rect`
- **THEN** HTTP JSON 的候选 object 包含 `best_rect`
- **AND** UI 候选列表展示该候选的最佳位置

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

### Requirement: UI 提供配置状态名候选
本地控制 UI SHALL 从 application 层获取当前配置中的界面状态名称，并把它们作为 dry-run 模拟状态输入的候选项。缺少状态配置时，系统 MUST 返回空候选列表且不阻止用户手动输入状态名。

#### Scenario: 页面加载状态候选
- **WHEN** 用户打开本地 UI 页面且 `assets/screen-states.json` 配置了 `主页` 和 `人物`
- **THEN** 页面可获取并展示 `主页` 与 `人物` 作为模拟状态输入候选

#### Scenario: 缺少配置时候选为空
- **WHEN** 用户打开本地 UI 页面但没有状态配置
- **THEN** 状态候选接口返回空列表
- **AND** 用户仍可手动输入模拟状态并运行脚本

### Requirement: UI 使用探测状态填充 dry-run 状态
本地控制 UI SHALL 允许用户把最近一次界面探测返回的非 `未知` 状态填入 dry-run 模拟状态输入。最近探测状态为 `未知` 或没有探测结果时，系统 MUST 保留用户当前输入且展示清晰提示。

#### Scenario: 使用已识别状态
- **GIVEN** 界面探测最近返回当前状态 `主页`
- **WHEN** 用户点击使用探测状态按钮
- **THEN** dry-run 模拟状态输入被设置为 `主页`

#### Scenario: 没有可用探测状态
- **GIVEN** 界面探测最近状态为 `未知`
- **WHEN** 用户点击使用探测状态按钮
- **THEN** dry-run 模拟状态输入保持不变
- **AND** 页面展示没有可用探测状态的提示

### Requirement: 真实脚本复用运行中的后台界面探测状态
本地控制 application SHALL 在真实脚本读取当前界面状态时优先复用正在运行的后台界面探测状态。只有后台探测正在运行且当前状态不是 `未知` 时，系统 MAY 复用该状态；否则 MUST 执行现有即时状态探测。

#### Scenario: 运行中的后台探测提供状态
- **GIVEN** 后台界面探测正在运行
- **AND** 最近探测状态为 `主页`
- **WHEN** 真实脚本评估 `ScreenStateIs("主页")`
- **THEN** 脚本状态 reader 返回 `主页`
- **AND** 系统不为该次状态读取额外执行即时探测
- **AND** 脚本运行日志说明状态来自后台界面探测

#### Scenario: 没有可用后台状态
- **GIVEN** 后台界面探测未运行或最近状态为 `未知`
- **WHEN** 真实脚本评估 `ScreenStateIs("主页")`
- **THEN** 系统执行即时状态探测获取当前状态

### Requirement: UI 展示选中脚本详情
本地控制 UI SHALL 在用户选择脚本时展示该脚本的可读详情。详情 MUST 包含脚本名称、步骤摘要和依赖摘要。HTTP adapter MUST 只委托 application 层生成详情，不得在入口层解释脚本模型。

#### Scenario: 展示状态驱动脚本详情
- **WHEN** 用户在本地 UI 选择包含 `ScreenStateIs("主页")` 的脚本
- **THEN** 页面展示该脚本名称
- **AND** 页面展示包含 `ScreenStateIs("主页")` 的步骤摘要
- **AND** 页面展示该脚本依赖界面状态 `主页`

#### Scenario: 未知脚本详情请求
- **WHEN** UI 请求不存在的脚本详情
- **THEN** 系统返回非零退出码和清晰错误消息

### Requirement: UI 展示脚本依赖检查结果
本地控制 UI SHALL 在脚本详情中展示运行前依赖检查结果。检查结果 MUST 由 application 层生成，HTTP adapter 和前端不得直接读取项目文件或解析状态配置。

#### Scenario: 图片依赖存在
- **WHEN** 选中脚本依赖图片 `assets/start.png`
- **AND** 该文件存在且后缀受支持
- **THEN** 脚本详情展示该图片依赖状态为可用

#### Scenario: 图片依赖缺失
- **WHEN** 选中脚本依赖图片 `assets/start.png`
- **AND** 该文件不存在
- **THEN** 脚本详情展示该图片依赖状态为缺失

#### Scenario: 状态依赖已配置
- **WHEN** 选中脚本依赖界面状态 `主页`
- **AND** 状态配置中存在 `主页`
- **THEN** 脚本详情展示该状态依赖状态为可用

#### Scenario: 状态依赖无法确认
- **WHEN** 选中脚本依赖界面状态 `主页`
- **AND** 状态配置不存在或无法读取
- **THEN** 脚本详情展示该状态依赖状态为无法确认

### Requirement: UI 使用脚本状态依赖填充 dry-run 状态
本地控制 UI SHALL 从脚本详情接口获取结构化界面状态依赖，并允许用户把当前选中脚本的第一个状态依赖填入 dry-run 模拟状态输入。HTTP adapter MUST 只转发 application 层生成的结构化状态依赖，不得通过解析展示文案推导状态依赖。

#### Scenario: 使用脚本状态依赖
- **WHEN** 用户选择包含 `ScreenStateIs("主页")` 的脚本
- **AND** 用户点击使用脚本状态按钮
- **THEN** dry-run 模拟状态输入被设置为 `主页`
- **AND** 页面展示已使用该脚本状态的提示

#### Scenario: 脚本没有状态依赖
- **WHEN** 用户选择不包含 `ScreenStateIs` 条件的脚本
- **AND** 用户点击使用脚本状态按钮
- **THEN** dry-run 模拟状态输入保持不变
- **AND** 页面展示当前脚本没有状态依赖的提示

#### Scenario: 脚本详情接口返回结构化状态依赖
- **WHEN** UI 请求包含 `ScreenStateIs("主页")` 的脚本详情
- **THEN** HTTP 响应包含结构化字段 `state_dependencies`
- **AND** `state_dependencies` 包含 `主页`

### Requirement: UI dry-run 使用脚本图片依赖
本地控制 UI SHALL 从脚本详情接口获取结构化图片依赖，并在 dry-run 运行当前脚本时把这些图片依赖作为 dry-run 图片命中模板提交给 application 层。HTTP adapter MUST 只转发前端提交的图片依赖列表，不得解析脚本展示文案；application 层 MUST 只在 dry-run 模式下把该列表传给脚本运行用例。

#### Scenario: 图片目标脚本 dry-run 成功
- **WHEN** 用户选择包含 `Click(ImageTarget(ImageTemplate("assets/start.png")))` 的脚本
- **AND** 用户在 UI 中以 dry-run 模式运行该脚本
- **THEN** UI 请求包含 `dry_run_images` 中的 `assets/start.png`
- **AND** application 层使用该图片作为 dry-run 命中模板
- **AND** 脚本按图片目标命中路径执行

#### Scenario: 真实运行忽略 dry-run 图片依赖
- **WHEN** 用户选择包含图片依赖的脚本
- **AND** 用户在 UI 中以真实运行模式运行该脚本
- **THEN** application 层不把 UI 提交的图片依赖作为 dry-run 命中模板
- **AND** 脚本继续通过真实桌面图像定位 adapter 查找图片

#### Scenario: 脚本详情接口返回结构化图片依赖
- **WHEN** UI 请求包含 `ImageExists(ImageTemplate("assets/start.png"))` 的脚本详情
- **THEN** HTTP 响应包含结构化字段 `image_dependencies`
- **AND** `image_dependencies` 包含 `assets/start.png`

### Requirement: UI dry-run 图片依赖解析命名图片
本地控制 UI SHALL 在生成结构化图片依赖时解析脚本资源目录中的命名图片引用。对于 `ImageExists(ImageRef(...))` 或 `Click(ImageTarget(ImageRef(...)))`，application 层 MUST 使用脚本 `resources` 将命名图片解析为对应 `ImageTemplate` 路径，并把该路径纳入 `image_dependencies`，使 UI dry-run 可继续通过既有 `dry_run_images` 请求字段提供模拟命中模板。

#### Scenario: 命名图片目标脚本 dry-run 成功
- **WHEN** 用户选择包含 `Click(ImageTarget(ImageRef("离开")))` 的脚本
- **AND** 脚本资源目录把 `离开` 解析为 `ImageTemplate("assets/离开.png")`
- **AND** 用户在 UI 中以 dry-run 模式运行该脚本
- **THEN** UI 请求包含 `dry_run_images` 中的 `assets/离开.png`
- **AND** application 层使用该图片作为 dry-run 命中模板
- **AND** 脚本按命名图片目标命中路径执行

#### Scenario: 脚本详情接口返回命名图片依赖路径
- **WHEN** UI 请求包含 `ImageExists(ImageRef("离开"))` 的脚本详情
- **AND** 脚本资源目录把 `离开` 解析为 `ImageTemplate("assets/离开.png")`
- **THEN** HTTP 响应字段 `image_dependencies` 包含 `assets/离开.png`

#### Scenario: 未知命名图片不生成 dry-run 命中模板
- **WHEN** UI 请求包含未知 `ImageRef("缺失")` 的脚本详情
- **THEN** HTTP 响应字段 `image_dependencies` 不包含 `缺失`
- **AND** 系统不为该未知引用生成 dry-run 图片路径

### Requirement: UI 依赖检查解析命名图片
本地控制 UI SHALL 在脚本详情依赖检查中解析脚本资源目录里的命名图片。对于 `ImageExists(ImageRef(...))` 或 `Click(ImageTarget(ImageRef(...)))`，application 层 MUST 使用脚本 `resources` 判断该命名图片是否已配置，并在已配置时继续检查解析后的 `ImageTemplate` 路径是否位于项目 `assets/` 目录且后缀受支持。

#### Scenario: 命名图片依赖可用
- **WHEN** 选中脚本依赖命名图片 `ImageRef("离开")`
- **AND** 脚本资源目录把 `离开` 解析为 `ImageTemplate("assets/离开.png")`
- **AND** `assets/离开.png` 文件存在且后缀受支持
- **THEN** 脚本详情展示该命名图片依赖状态为可用

#### Scenario: 命名图片文件缺失
- **WHEN** 选中脚本依赖命名图片 `ImageRef("离开")`
- **AND** 脚本资源目录把 `离开` 解析为 `ImageTemplate("assets/离开.png")`
- **AND** `assets/离开.png` 文件不存在
- **THEN** 脚本详情展示该命名图片依赖状态为缺失

#### Scenario: 命名图片未配置
- **WHEN** 选中脚本依赖命名图片 `ImageRef("缺失")`
- **AND** 脚本资源目录没有配置 `缺失`
- **THEN** 脚本详情展示该命名图片依赖状态为缺失
- **AND** 页面消息说明命名图片未配置

### Requirement: UI 展示界面探测统计
本地控制 UI SHALL 在界面状态探测状态中展示结构化统计。HTTP 状态查询 payload MUST 包含统计对象；页面 MUST 展示已完成轮数、最近一轮耗时、状态命中次数和候选跳过次数。没有后台探测会话时，系统 MUST 返回空统计。

#### Scenario: 查询探测状态包含统计
- **WHEN** 页面轮询 `/api/screen-state-probe`
- **THEN** HTTP 响应包含界面探测统计对象
- **AND** 统计对象包含已完成轮数和最近一轮耗时

#### Scenario: 页面展示命中频率
- **WHEN** 后台界面状态探测已经命中 `主页` 两次、`人物` 一次
- **THEN** 页面展示 `主页` 与 `人物` 的命中次数

#### Scenario: 没有探测会话时统计为空
- **WHEN** 页面在没有后台界面状态探测会话时查询状态
- **THEN** HTTP 响应中的统计对象表示 0 轮探测且没有命中或跳过计数

### Requirement: UI 展示界面状态配置摘要
本地控制 UI SHALL 在界面探测 tab 展示当前界面状态配置摘要。HTTP adapter MUST 提供配置摘要接口，并只委托 application 层生成摘要。页面 MUST 展示状态名、搜索项、图片路径、区域信息和最低置信度；没有配置或配置非法时 MUST 展示清晰提示。

#### Scenario: 页面加载状态配置摘要
- **WHEN** 用户打开本地 UI 页面且状态配置有效
- **THEN** 页面通过 HTTP 接口获取并展示状态配置摘要

#### Scenario: 没有状态配置
- **WHEN** 用户打开本地 UI 页面但没有 `assets/screen-states.json`
- **THEN** 页面展示未配置状态识别
- **AND** 页面仍允许用户启动界面探测

#### Scenario: 状态配置非法
- **WHEN** 状态配置摘要接口返回非零退出码
- **THEN** 页面展示配置错误消息
- **AND** 页面不尝试在前端解析配置文件

### Requirement: UI 展示脚本状态决策摘要
本地控制 UI SHALL 在脚本详情中展示状态驱动决策摘要。脚本详情 HTTP payload MUST 包含结构化字段 `state_decisions`；每个决策 MUST 包含状态名、状态命中时执行的步骤摘要，以及状态未命中时执行的步骤摘要。该摘要 MUST 由 application 层生成，HTTP adapter 和前端不得直接解释脚本步骤模型。

#### Scenario: 展示状态分支决策
- **WHEN** 用户选择包含 `If(ScreenStateIs("主页"))` 的脚本
- **THEN** 脚本详情 payload 包含状态决策 `主页`
- **AND** 页面展示状态为 `主页` 时执行的步骤摘要

#### Scenario: 展示状态未命中分支
- **WHEN** 状态分支包含 else 步骤
- **THEN** 状态决策摘要包含状态未命中时执行的步骤摘要

#### Scenario: 没有状态决策
- **WHEN** 用户选择不包含 `If(ScreenStateIs(...))` 的脚本
- **THEN** 页面展示没有状态决策

### Requirement: UI 预览脚本状态决策当前分支
本地控制 UI SHALL 在脚本详情的状态决策摘要中，结合最近一次界面探测状态展示当前预览分支。该预览 MUST 只使用脚本详情 payload 中的结构化 `state_decisions` 和前端已收到的探测状态，不得在前端解析脚本文案或改变脚本执行结果。

#### Scenario: 当前状态命中决策
- **GIVEN** 页面最近一次界面探测状态为 `主页`
- **WHEN** 用户选择包含状态决策 `主页` 的脚本
- **THEN** 脚本详情展示该决策当前预览为命中

#### Scenario: 当前状态未命中决策
- **GIVEN** 页面最近一次界面探测状态为 `人物`
- **WHEN** 用户选择包含状态决策 `主页` 的脚本
- **THEN** 脚本详情展示该决策当前预览为未命中

#### Scenario: 当前状态未知
- **GIVEN** 页面还没有可用界面探测状态或最近状态为 `未知`
- **WHEN** 用户选择包含状态决策的脚本
- **THEN** 脚本详情展示该决策当前预览为未知

#### Scenario: 探测状态更新后刷新预览
- **GIVEN** 页面已经展示包含状态决策 `主页` 的脚本详情
- **WHEN** 界面探测轮询更新最近状态为 `主页`
- **THEN** 脚本详情中的当前预览刷新为命中

### Requirement: UI 展示最近界面候选结果
本地控制 UI SHALL 在界面状态探测状态中展示最近一轮候选结果。HTTP 状态查询 payload MUST 包含结构化候选结果列表；页面 MUST 展示候选名称、结果状态、耗时和置信度。没有候选结果时，页面 MUST 展示清晰提示。

#### Scenario: 查询探测状态包含候选结果
- **WHEN** 页面轮询 `/api/screen-state-probe` 且后台探测已经完成一轮
- **THEN** HTTP 响应包含最近一轮候选结果列表
- **AND** 每个候选结果包含候选名称、结果状态、耗时和置信度

#### Scenario: 页面展示候选命中和跳过
- **WHEN** 后台界面状态探测最近一轮中 `主页` 命中，`人物` 被早停跳过
- **THEN** 页面展示 `主页` 为命中
- **AND** 页面展示 `人物` 为跳过

#### Scenario: 没有候选结果
- **WHEN** 页面查询探测状态但后台探测尚未完成任何一轮
- **THEN** 页面展示暂无候选结果

### Requirement: UI 展示界面候选搜索项名称
本地控制 UI SHALL 在最近界面候选结果中展示配置搜索项名称。HTTP 状态查询 payload MUST 为每个候选结果包含 `search_name` 字段；当该字段存在时，页面 MUST 同时展示状态名和搜索项名。

#### Scenario: HTTP 候选结果包含搜索项名称
- **WHEN** 页面轮询 `/api/screen-state-probe` 且最近候选来自搜索项 `离开按钮`
- **THEN** HTTP 响应候选结果包含 `search_name` 为 `离开按钮`

#### Scenario: 页面展示状态和搜索项
- **WHEN** 最近候选结果的状态名为 `战斗失败`，搜索项名称为 `离开按钮`
- **THEN** 页面展示 `战斗失败 / 离开按钮`

#### Scenario: 无搜索项名称时只展示状态名
- **WHEN** 最近候选结果没有搜索项名称
- **THEN** 页面只展示状态名

### Requirement: UI 脚本详情解析搜索别名图片依赖
本地控制 UI SHALL 在脚本详情中解析 `ImageExists(SearchRef(...))` 和 `ImageTarget(SearchRef(...))` 的图片依赖。解析成功时，结构化 `image_dependencies` MUST 包含搜索别名最终指向的图片路径，依赖检查 MUST 报告该图片文件是否可用；解析失败时，依赖检查 MUST 报告搜索别名缺失。

#### Scenario: 搜索别名图片依赖可用
- **WHEN** 选中脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **AND** 脚本资源目录把 `离开按钮` 解析到 `assets/离开.png`
- **AND** 图片文件存在且后缀受支持
- **THEN** 脚本详情 `image_dependencies` 包含 `assets/离开.png`
- **AND** 依赖检查展示该搜索别名图片依赖可用

#### Scenario: 搜索别名缺失
- **WHEN** 选中脚本包含 `ImageExists(SearchRef("缺失搜索"))`
- **AND** 脚本资源目录没有配置该搜索别名
- **THEN** 脚本详情依赖检查展示搜索别名未配置

#### Scenario: 搜索别名参与 dry-run 图片依赖
- **WHEN** 用户选择包含搜索别名图片目标的脚本
- **AND** 用户在 UI 中以 dry-run 模式运行该脚本
- **THEN** UI 请求中的 `dry_run_images` 包含搜索别名解析出的图片路径

### Requirement: UI 脚本可复用状态配置搜索别名
本地控制 application SHALL 允许 UI 运行和展示命名脚本时复用 `assets/screen-states.json` 中配置的搜索别名。系统 MUST 在进入脚本详情、同步运行或后台运行前把状态配置中的搜索项作为共享脚本资源注入；脚本自身资源 MUST 覆盖共享资源中的同名资源。

#### Scenario: 脚本详情解析状态配置搜索别名
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮` 并指向 `assets/离开.png`
- **AND** 脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **THEN** 脚本详情 `image_dependencies` 包含 `assets/离开.png`
- **AND** 依赖检查展示该搜索别名图片依赖可用

#### Scenario: dry-run 运行使用状态配置搜索别名
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮`
- **AND** 脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **AND** 用户以 dry-run 模式运行脚本
- **THEN** application 使用状态配置中的搜索别名解析图片目标

#### Scenario: 脚本资源覆盖共享搜索别名
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮` 指向 `assets/配置.png`
- **AND** 脚本自身资源也配置搜索 `离开按钮` 指向 `assets/脚本.png`
- **THEN** 脚本详情和运行均使用脚本自身资源中的 `assets/脚本.png`

### Requirement: UI 生成界面探测诊断截图

本地控制 UI SHALL 提供探测诊断入口，用于执行一轮界面状态探测并展示带候选最佳匹配框的诊断截图。HTTP adapter MUST 只把请求委托给 application 层，UI MUST 展示退出码、输出信息和诊断图片。

#### Scenario: 页面展示探测诊断入口

- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示用于生成界面探测诊断截图的按钮

#### Scenario: 生成并展示探测诊断截图

- **WHEN** 用户点击探测诊断按钮
- **THEN** 系统执行一轮界面状态探测并保存诊断截图
- **AND** UI 在诊断预览区域展示该图片

#### Scenario: 探测诊断失败

- **WHEN** 状态探测、截图或屏幕尺寸不可用
- **THEN** 系统返回非零退出码和清晰错误消息
- **AND** UI 展示错误消息

### Requirement: UI 触发状态裁剪导出

本地控制 UI SHALL 提供状态区域裁剪和探测候选裁剪导出入口。HTTP adapter MUST 只把请求委托给 application 层裁剪导出用例，并把 application 返回的退出码、stdout 和 stderr 展示给用户。

#### Scenario: 页面展示裁剪导出入口

- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示区域裁剪导出按钮
- **AND** 页面展示探测候选裁剪导出按钮

#### Scenario: 导出状态区域裁剪

- **WHEN** 用户点击区域裁剪导出按钮
- **THEN** UI 调用区域裁剪导出接口
- **AND** HTTP adapter 调用 application 层区域裁剪导出用例
- **AND** UI 展示 application 返回的输出和错误信息

#### Scenario: 导出探测候选裁剪

- **WHEN** 用户点击探测候选裁剪导出按钮
- **THEN** UI 调用探测候选裁剪导出接口
- **AND** HTTP adapter 把当前最低置信度传给 application 层候选裁剪导出用例
- **AND** UI 展示 application 返回的输出和错误信息

### Requirement: 本地 UI 提供屏幕识别环境诊断入口

本地控制 UI SHALL 提供屏幕识别环境诊断入口，用于从浏览器触发一次截图诊断和单轮界面状态探测。HTTP adapter MUST 委托 application 层组合用例，UI MUST 展示退出码、stdout、stderr 和诊断截图。

#### Scenario: 页面提供环境诊断按钮
- **WHEN** 用户打开本地 UI 页面
- **THEN** 页面展示屏幕识别环境诊断按钮
- **AND** 前端脚本会向 `/api/diagnose-screen` 发起请求

#### Scenario: HTTP 触发环境诊断
- **WHEN** UI 向 `/api/diagnose-screen` 提交最低置信度
- **THEN** HTTP adapter 调用 application 层屏幕诊断用例
- **AND** payload 包含退出码、stdout、stderr、截图路径和截图预览 URL

#### Scenario: 非法最低置信度
- **WHEN** UI 向 `/api/diagnose-screen` 提交非数字最低置信度
- **THEN** HTTP adapter 不调用 application 层屏幕诊断用例
- **AND** payload 返回配置错误和清晰错误原因

### Requirement: UI 状态配置摘要展示最近匹配结果

本地控制 UI SHALL 在界面状态配置摘要中，为每个配置搜索项展示最近一次界面探测候选结果。页面 MUST 使用结构化配置摘要和最近候选结果进行关联，不得解析展示文本；当没有最近候选结果时，页面 MUST 显示该搜索项暂无最近结果。

#### Scenario: 配置搜索项展示最近命中
- **WHEN** 状态配置包含状态 `主页` 的搜索项 `主页标识`
- **AND** 最近候选结果包含 `name=主页`、`search_name=主页标识`、`status=matched`
- **THEN** 状态配置摘要在该搜索项下展示最近结果为命中
- **AND** 展示最近置信度、最佳置信度和最佳位置

#### Scenario: 配置搜索项展示最近未命中
- **WHEN** 状态配置包含状态 `人物` 的搜索项 `人物标识`
- **AND** 最近候选结果包含 `name=人物`、`search_name=人物标识`、`status=missed`
- **THEN** 状态配置摘要在该搜索项下展示最近结果为未命中
- **AND** 展示最佳置信度和最佳位置

#### Scenario: 配置搜索项没有最近结果
- **WHEN** 状态配置包含状态 `活动` 的搜索项 `活动标识`
- **AND** 最近候选结果中没有对应的状态和搜索项
- **THEN** 状态配置摘要在该搜索项下展示最近结果为暂无

#### Scenario: 探测状态更新后刷新配置摘要
- **WHEN** 页面已经展示状态配置摘要
- **AND** `/api/screen-state-probe` 轮询返回新的候选结果
- **THEN** 页面重新渲染状态配置摘要中的最近结果
