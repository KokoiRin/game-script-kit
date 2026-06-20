# script-management Specification

## Purpose
定义脚本管理能力（`scripts_manager` 包），使具名脚本可被集中保存、查找和通过 `star` CLI 按名称启动。
## Requirements
### Requirement: 命名脚本可被集中管理

系统 SHALL 在 `scripts_manager.catalog` 中提供 `ScriptCatalog`，用于集中保存和通过名称查找多个具名 `Script` 定义。

#### Scenario: 列出所有脚本

- **WHEN** 调用方请求查看可用脚本
- **THEN** 系统会返回所有已注册脚本的名称

#### Scenario: 按名称读取脚本

- **WHEN** 调用方使用已存在的脚本名称读取脚本
- **THEN** 系统会返回对应的 `Script` 定义

#### Scenario: 未知脚本名称被拒绝

- **WHEN** 调用方使用不存在的脚本名称读取脚本
- **THEN** 系统会拒绝请求，并报告脚本名称不存在

#### Scenario: 重复脚本名称被拒绝

- **WHEN** 系统加载多个名称相同的脚本定义
- **THEN** 系统会拒绝脚本集合，并报告脚本名称重复

### Requirement: 脚本定义可独立编辑

系统 SHALL 将脚本定义放在 `scripts_manager` 中，与 `engine` 和 `adapters` 分离，使用户可以编辑某个脚本而不需要修改 runner 或平台 adapter。

#### Scenario: 编辑脚本动作不影响 runner

- **WHEN** 用户修改 `scripts_manager` 中某个脚本定义的动作序列
- **THEN** `ScriptRunner` 和 `InputDevice` adapter 不需要同步修改即可执行更新后的脚本

#### Scenario: 新增脚本不需要新增专用 CLI

- **WHEN** 用户新增一个脚本定义并注册到 `ScriptCatalog` 中
- **THEN** 用户可以通过 `star run <name>` 按名称启动该脚本

### Requirement: CLI 支持按名称启动脚本

系统 SHALL 提供 `star` 命令行入口，允许用户通过脚本名称选择并启动脚本。

#### Scenario: dry-run 指定脚本

- **WHEN** 用户通过 `star run <name> --dry-run` 运行脚本
- **THEN** 系统会使用 `DryRunInputDevice` 按该脚本的动作顺序即时打印计划执行的操作，而不移动真实鼠标

#### Scenario: macOS 模式指定脚本

- **WHEN** 用户通过 `star run <name>` 运行脚本（默认使用 macOS adapter）
- **THEN** 系统会加载 macOS `InputDevice` adapter 并执行该脚本

#### Scenario: CLI 报告未知脚本

- **WHEN** 用户通过 `star run <name>` 指定不存在的脚本名称
- **THEN** 系统会返回非零退出码，并提示该脚本不存在

### Requirement: CLI dry-run 支持条件分支脚本
系统 SHALL 允许用户通过 `star run <name> --dry-run` 验证包含颜色条件分支的脚本。dry-run 模式 MUST 使用可预测的颜色读取实现，而不读取真实屏幕。

#### Scenario: dry-run 使用默认固定颜色
- **WHEN** 用户通过 `star run <name> --dry-run` 运行条件分支脚本且未指定 dry-run 颜色
- **THEN** 系统会使用默认固定颜色评估颜色条件，并打印对应分支的计划操作

#### Scenario: dry-run 使用用户指定颜色
- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-color #RRGGBB` 运行条件分支脚本
- **THEN** 系统会使用用户指定颜色评估颜色条件，并打印对应分支的计划操作

#### Scenario: 默认 catalog 包含条件分支示例脚本
- **WHEN** 用户列出默认脚本
- **THEN** 结果中包含一个可用于验证颜色条件分支的示例脚本

### Requirement: CLI 真实运行注入颜色读取 adapter
系统 SHALL 在真实运行包含颜色条件分支的脚本时注入桌面取色 adapter，使 runner 可以通过 `PixelColorReader` 端口评估颜色条件。

#### Scenario: macOS 模式运行条件分支脚本
- **WHEN** 用户通过 `star run <name>` 运行条件分支脚本
- **THEN** 系统会同时加载输入设备 adapter 和颜色读取 adapter，并把它们注入 ScriptRunner

#### Scenario: 颜色读取 adapter setup 失败被报告
- **WHEN** 真实运行时颜色读取 adapter 因依赖、权限或运行环境不可用而初始化失败
- **THEN** CLI 会返回非零退出码，并向用户报告脚本运行 setup 失败

### Requirement: CLI dry-run 支持条件等待示例脚本
系统 SHALL 提供一个默认注册的条件等待示例脚本，使用户可以通过 `star run <name> --dry-run` 验证 `WaitUntil(ColorIs(...))` 的成功和超时路径。

#### Scenario: 默认 catalog 包含条件等待示例脚本
- **WHEN** 用户列出默认脚本
- **THEN** 结果中包含一个可用于验证条件等待的示例脚本

#### Scenario: dry-run 验证条件等待成功路径
- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-color #RRGGBB` 提供满足条件的固定颜色
- **THEN** 系统会立即通过条件等待，并打印后续计划操作

#### Scenario: dry-run 验证条件等待超时路径
- **WHEN** 用户通过 `star run <name> --dry-run` 使用不满足条件的默认固定颜色
- **THEN** 系统会按等待间隔打印计划等待操作，并以非零退出码报告条件等待超时

### Requirement: CLI dry-run 支持图片条件脚本
系统 SHALL 允许用户通过 `star run <name> --dry-run` 验证包含图片存在条件的脚本。dry-run 模式 MUST 使用可预测的图像定位实现，而不读取真实屏幕。

#### Scenario: dry-run 默认图片不存在
- **WHEN** 用户通过 `star run <name> --dry-run` 运行图片条件脚本且未指定 dry-run 图片
- **THEN** 系统会使用默认未找到结果评估图片条件，并打印对应计划操作或等待超时结果

#### Scenario: dry-run 指定图片存在
- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-image <template-path>` 运行图片条件脚本
- **THEN** 系统会对指定模板返回预设匹配结果，并按图片条件满足路径打印计划操作

#### Scenario: 默认 catalog 包含图片等待示例脚本
- **WHEN** 用户列出默认脚本
- **THEN** 结果中包含一个可用于验证 `WaitUntil(ImageExists(...))` 的示例脚本

### Requirement: CLI 真实运行注入图像定位 adapter
系统 SHALL 在真实运行包含图片存在条件的脚本时注入桌面图像定位 adapter，使 runner 可以通过 `ScreenImageLocator` 端口评估图片条件。

#### Scenario: macOS 模式运行图片条件脚本
- **WHEN** 用户通过 `star run <name>` 运行图片条件脚本
- **THEN** 系统会同时加载输入设备 adapter 和图像定位 adapter，并把它们注入 ScriptRunner

#### Scenario: 图像定位 adapter setup 失败被报告
- **WHEN** 真实运行时图像定位 adapter 因依赖、模板路径、权限或运行环境不可用而初始化或匹配失败
- **THEN** CLI 会返回非零退出码，并向用户报告脚本运行 setup 或运行失败

### Requirement: CLI dry-run 支持图片条件等待示例脚本
系统 SHALL 提供一个默认注册的图片条件等待示例脚本，使用户可以通过 `star run <name> --dry-run` 验证 `WaitUntil(ImageExists(...))` 的成功和超时路径。

#### Scenario: dry-run 验证图片条件等待成功路径
- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-image <template-path>` 提供满足条件的模板图片路径
- **THEN** 系统会立即通过图片条件等待，并打印后续计划操作

#### Scenario: dry-run 验证图片条件等待超时路径
- **WHEN** 用户通过 `star run <name> --dry-run` 使用默认未找到结果
- **THEN** 系统会按等待间隔打印计划等待操作，并以非零退出码报告条件等待超时

### Requirement: CLI dry-run 支持图片目标点击脚本
系统 SHALL 允许用户通过 `star run <name> --dry-run --dry-run-image <template-path>` 验证包含图片目标点击的脚本。dry-run 模式 MUST 使用可预测的图像定位实现，而不读取真实屏幕。

#### Scenario: dry-run 图片目标点击成功
- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-image <template-path>` 运行图片目标点击脚本
- **THEN** 系统会对指定模板返回预设匹配结果，并打印解析后的点击坐标

#### Scenario: dry-run 图片目标点击未找到
- **WHEN** 用户通过 `star run <name> --dry-run` 运行图片目标点击脚本且未指定 dry-run 图片
- **THEN** 系统会返回非零退出码，并报告图片目标未找到

#### Scenario: 默认 catalog 包含图片目标点击示例脚本
- **WHEN** 用户列出默认脚本
- **THEN** 结果中包含一个可用于验证 `Click(ImageTarget(...))` 的示例脚本

### Requirement: CLI 真实运行注入图片目标点击所需 adapter
系统 SHALL 在真实运行包含图片目标点击的脚本时注入桌面图像定位 adapter，使 runner 可以通过 `ScreenImageLocator` 端口解析点击坐标。

#### Scenario: macOS 模式运行图片目标点击脚本
- **WHEN** 用户通过 `star run <name>` 运行图片目标点击脚本
- **THEN** 系统会同时加载输入设备 adapter 和图像定位 adapter，并把它们注入 ScriptRunner

#### Scenario: 图片目标点击运行失败被报告
- **WHEN** 真实运行时图像定位 adapter 因依赖、模板路径、权限、未找到图片或运行环境不可用而失败
- **THEN** CLI 会返回非零退出码，并向用户报告脚本运行失败

### Requirement: CLI 脚本复用状态配置搜索别名
系统 SHALL 允许 `star run` 运行的命名脚本复用 `assets/screen-states.json` 中配置的搜索别名。CLI MUST 在调用脚本运行用例前把状态配置中的搜索项作为共享脚本资源注入；脚本自身资源 MUST 覆盖共享资源中的同名资源。

#### Scenario: dry-run 运行状态配置搜索别名脚本
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮` 并指向 `assets/离开.png`
- **AND** 命名脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **AND** 用户运行 `star run <name> --dry-run --dry-run-image <assets/离开.png>`
- **THEN** CLI 使用状态配置中的搜索别名解析图片目标并打印 dry-run 点击输出

#### Scenario: 缺少状态配置不影响普通脚本
- **WHEN** 项目没有 `assets/screen-states.json`
- **AND** 用户运行不依赖搜索别名的命名脚本
- **THEN** CLI 继续按原有方式运行脚本

#### Scenario: 脚本资源覆盖共享搜索别名
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮` 指向 `assets/配置.png`
- **AND** 脚本自身资源也配置搜索 `离开按钮` 指向 `assets/脚本.png`
- **THEN** CLI 使用脚本自身资源中的搜索定义

### Requirement: CLI 展示脚本详情
系统 SHALL 提供 `star details <name>` 子命令，用于展示命名脚本的步骤、外部依赖、图片 dry-run 依赖和运行前检查。CLI MUST 复用 application 层脚本详情生成能力，不得在入口层解释脚本步骤语义。

#### Scenario: 展示普通脚本详情
- **WHEN** 用户运行 `star details <name>`
- **THEN** CLI 输出脚本名称、步骤摘要、依赖摘要、图片依赖和依赖检查结果

#### Scenario: 详情解析状态配置搜索别名
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮`
- **AND** 命名脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **AND** 用户运行 `star details <name>`
- **THEN** CLI 输出包含该搜索别名解析出的图片依赖

#### Scenario: 未知脚本详情
- **WHEN** 用户运行 `star details <missing>`
- **THEN** CLI 返回非零退出码并提示脚本不存在

### Requirement: CLI dry-run 可自动使用脚本图片依赖
系统 SHALL 允许用户通过 `star run <name> --dry-run --dry-run-script-images` 自动把脚本详情解析出的图片依赖作为 dry-run 命中图片。该能力 MUST 复用 application 层脚本详情生成的 `image_dependencies`，不得在 CLI 入口层解释脚本步骤语义。

#### Scenario: 自动 dry-run 图片目标点击
- **WHEN** 命名脚本包含 `Click(ImageTarget(ImageTemplate("assets/start.png")))`
- **AND** 用户运行 `star run <name> --dry-run --dry-run-script-images`
- **THEN** CLI 把 `assets/start.png` 作为 dry-run 命中图片并打印点击输出

#### Scenario: 自动 dry-run 搜索别名图片目标
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮`
- **AND** 命名脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **AND** 用户运行 `star run <name> --dry-run --dry-run-script-images`
- **THEN** CLI 把搜索别名解析出的图片路径作为 dry-run 命中图片并打印点击输出

#### Scenario: 默认 dry-run 不自动命中图片
- **WHEN** 用户运行图片目标脚本且只提供 `--dry-run`
- **THEN** CLI 继续按图片未找到路径返回非零结果

#### Scenario: 非 dry-run 拒绝自动图片依赖开关
- **WHEN** 用户运行 `star run <name> --dry-run-script-images` 但没有提供 `--dry-run`
- **THEN** CLI 返回配置错误且不运行脚本

### Requirement: CLI 真实运行注入界面状态读取 adapter

系统 SHALL 在真实运行包含 `ScreenStateIs` 条件的命名脚本时注入本地桌面界面状态读取 adapter，使 runner 可以通过 `ScreenStateReader` 端口参考当前识别到的界面状态。CLI MUST 复用 application 层状态探测 reader，不得在入口层执行图片匹配或解释状态识别规则。

#### Scenario: macOS 模式运行界面状态条件脚本

- **WHEN** 用户通过 `star run <name>` 真实运行包含 `ScreenStateIs("主页")` 的命名脚本
- **THEN** 系统会同时加载输入设备 adapter 和界面状态读取 adapter，并把它们注入 ScriptRunner

#### Scenario: dry-run 状态条件脚本仍使用固定状态

- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-screen-state 主页` 运行包含 `ScreenStateIs("主页")` 的命名脚本
- **THEN** 系统继续使用 dry-run 固定状态评估条件
- **AND** 不读取真实屏幕状态

### Requirement: CLI dry-run 支持使用当前探测界面状态

系统 SHALL 允许用户通过 `star run <name> --dry-run --dry-run-probed-screen-state` 在运行 dry-run 前执行一轮界面状态探测，并把探测结果的 `current_state` 作为本次 dry-run 的固定界面状态。CLI MUST 复用 application 层状态探测用例，不得在入口层执行图片匹配或解释状态识别规则。

#### Scenario: dry-run 使用当前探测状态

- **WHEN** 用户运行 `star run <name> --dry-run --dry-run-probed-screen-state`
- **AND** 单次界面状态探测返回当前状态 `主页`
- **AND** 命名脚本包含 `ScreenStateIs("主页")`
- **THEN** CLI 使用 `主页` 作为本次 dry-run 状态条件输入
- **AND** dry-run 按状态命中分支输出计划操作

#### Scenario: 参数要求 dry-run 模式

- **WHEN** 用户运行 `star run <name> --dry-run-probed-screen-state` 但未提供 `--dry-run`
- **THEN** CLI 返回配置错误且不运行脚本

#### Scenario: 状态来源冲突

- **WHEN** 用户同时提供 `--dry-run-probed-screen-state` 和 `--dry-run-screen-state 主页`
- **THEN** CLI 返回配置错误且不运行脚本

#### Scenario: 探测配置错误

- **WHEN** 状态配置非法
- **AND** 用户运行 `star run <name> --dry-run --dry-run-probed-screen-state`
- **THEN** CLI 返回配置错误并把原因写入 stderr
- **AND** 不运行脚本

#### Scenario: 探测运行失败

- **WHEN** 图像定位 adapter 不可用
- **AND** 用户运行 `star run <name> --dry-run --dry-run-probed-screen-state`
- **THEN** CLI 返回运行错误并把原因写入 stderr
- **AND** 不运行脚本

### Requirement: 默认脚本包含界面状态等待示例

系统 SHALL 在默认脚本 catalog 中提供 `wait-until-screen-state-demo`，用于展示脚本如何等待当前界面状态达到指定值后继续执行。该脚本 MUST 使用 `WaitUntil(ScreenStateIs("主页"))` 表达等待语义，并在等待成功后执行后续示例动作。

#### Scenario: 默认 catalog 列出状态等待示例

- **WHEN** 用户运行 `star list`
- **THEN** 输出包含 `wait-until-screen-state-demo`

#### Scenario: 详情展示状态等待步骤

- **WHEN** 用户运行 `star details wait-until-screen-state-demo`
- **THEN** 输出包含 `WaitUntil ScreenStateIs("主页")`
- **AND** 输出包含状态依赖检查结果

#### Scenario: dry-run 状态等待成功

- **WHEN** 用户运行 `star run wait-until-screen-state-demo --dry-run --dry-run-screen-state 主页`
- **THEN** dry-run 使用 `主页` 作为当前界面状态
- **AND** 脚本继续执行等待后的示例动作

### Requirement: 脚本详情展示状态等待摘要

系统 SHALL 在脚本详情中展示 `WaitUntil(ScreenStateIs(...))` 的状态等待摘要，使用户可以区分“脚本根据状态分支”和“脚本等待某个状态后继续”。该摘要 MUST 由 application 层脚本详情能力生成，CLI 和 UI 入口不得自行解析脚本步骤文本。

#### Scenario: CLI 展示状态等待

- **WHEN** 用户运行 `star details wait-until-screen-state-demo`
- **THEN** CLI 输出包含“状态等待”分组
- **AND** 输出包含 `等待状态: 主页`

#### Scenario: UI 详情接口返回状态等待

- **WHEN** UI 通过 `/api/script-details` 请求包含 `WaitUntil(ScreenStateIs("主页"))` 的脚本详情
- **THEN** JSON payload 包含 `state_waits` 字段
- **AND** `state_waits` 包含 `主页`

#### Scenario: UI 使用当前探测状态预览等待满足情况

- **WHEN** UI 已获得当前探测状态 `主页`
- **AND** 当前脚本详情包含状态等待 `主页`
- **THEN** 脚本详情展示该状态等待当前已满足
