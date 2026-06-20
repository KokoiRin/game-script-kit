# screen-state-probe Specification

## Purpose
TBD - created by archiving change add-screen-state-probe-ui. Update Purpose after archive.
## Requirements
### Requirement: 界面状态探测返回当前状态
系统 SHALL 提供一轮界面状态探测能力，对多个候选界面图片执行匹配，并返回当前识别到的状态。候选图片命中时 SHALL 记录候选名称、是否命中、置信度和耗时；没有候选命中时 SHALL 返回未知状态。

#### Scenario: 探测到匹配状态
- **WHEN** 一轮探测中候选 `装备` 的图片匹配成功且其他候选未匹配成功
- **THEN** 探测结果的当前状态为 `装备`，并包含 `装备` 候选的命中详情

#### Scenario: 没有候选命中
- **WHEN** 一轮探测中所有候选图片都未匹配成功
- **THEN** 探测结果的当前状态为 `未知`，并保留每个候选的未命中详情

#### Scenario: 多个候选命中
- **WHEN** 一轮探测中多个候选图片匹配成功
- **THEN** 探测结果选择置信度最高的候选作为当前状态，并保留所有候选详情

### Requirement: 界面状态探测使用图片资源目录
系统 SHALL 使用项目 `assets/` 目录中的支持图片文件作为第一版界面候选来源。每张候选图片的文件名主干 SHALL 作为界面状态名称。

#### Scenario: 从图片资源生成候选状态
- **WHEN** `assets/` 中存在 `人物.png` 和 `装备.webp`
- **THEN** 界面状态探测候选包含 `人物` 和 `装备`

### Requirement: 界面状态循环探测可停止
系统 SHALL 支持后台循环执行界面状态探测。每轮探测 MUST 在上一轮完成后才开始下一轮，并且停止请求 MUST 让循环在当前轮结束后退出。

#### Scenario: 循环探测追加日志
- **WHEN** 用户启动界面状态探测
- **THEN** 系统在后台反复执行探测，并追加每轮当前状态、总耗时和候选匹配摘要日志

#### Scenario: 停止循环探测
- **WHEN** 用户请求停止正在运行的界面状态探测
- **THEN** 系统标记停止请求，并在当前匹配轮结束后返回已停止状态

### Requirement: 界面状态探测优先使用批量图片定位
系统 SHALL 在界面状态探测中优先使用批量图片定位能力。已装配批量定位 adapter 时，一轮界面状态探测 MUST 只请求一次批量定位；未装配批量定位 adapter 时，系统 MAY 回退到逐个单图定位。

#### Scenario: 使用批量定位探测界面
- **WHEN** application 层已装配批量图片定位 adapter 且用户启动界面状态探测
- **THEN** 每轮界面状态探测通过一次批量定位请求匹配所有候选图片

#### Scenario: 回退到单图定位
- **WHEN** 界面状态探测未装配批量图片定位 adapter 但已装配单图定位 adapter
- **THEN** 系统继续逐个匹配候选图片并返回同样形状的探测结果

### Requirement: 界面状态探测按候选优先级早停
系统 SHALL 在界面状态探测中默认按候选顺序早停。候选顺序 MUST 表示探测优先级；找到第一个命中候选后，本轮不再匹配后续候选，当前状态为该命中候选。

#### Scenario: 按候选顺序早停
- **WHEN** 一轮界面状态探测候选顺序为 `主页`、`人物`、`技能`
- **AND** `主页` 匹配成功
- **THEN** 当前状态为 `主页`
- **AND** `人物` 与 `技能` 在本轮结果中标记为 skipped

#### Scenario: 未命中候选不会提前停止
- **WHEN** 一轮界面状态探测中前两个候选未命中
- **THEN** 系统继续匹配后续候选直到命中或耗尽全部候选

### Requirement: 界面状态探测候选使用图片搜索规格
系统 SHALL 允许界面状态候选使用图片搜索规格表达待匹配图片、搜索区域和最低置信度。候选没有显式搜索区域时 SHALL 继续表示全屏搜索。

#### Scenario: 候选携带搜索区域
- **WHEN** `人物` 状态候选使用图片 `人物.png` 和区域 `右侧面板`
- **THEN** 一轮界面状态探测只在该区域内匹配 `人物.png`

#### Scenario: 旧候选表示全屏搜索
- **WHEN** 系统从 `assets/人物.png` 生成兼容候选
- **THEN** 该候选使用 `人物.png` 和空搜索区域

### Requirement: 界面状态探测支持状态组配置文档
系统 SHALL 支持从 `assets/screen-states.json` 读取界面状态组配置。配置文档 MUST 能声明命名区域、状态组和每个状态组内的图片搜索项。存在该配置文档时，状态探测候选 SHALL 来自配置文档；不存在时，系统 SHALL 回退到扫描 `assets/` 图片文件。

#### Scenario: 从配置文档生成状态组候选
- **WHEN** `assets/screen-states.json` 声明状态 `战斗失败`，并包含 `离开按钮` 与 `重来按钮` 两个搜索项
- **THEN** 界面状态探测会把这两个搜索项作为同一个状态组的候选标识

#### Scenario: 配置文档控制搜索区域
- **WHEN** 配置文档声明 `离开按钮` 使用命名区域 `右上弹窗`
- **THEN** 一轮状态探测会把 `右上弹窗` 解析为该搜索项的搜索区域

#### Scenario: 没有配置文档时回退到 assets 扫描
- **WHEN** `assets/screen-states.json` 不存在
- **THEN** 系统继续把 `assets/` 目录中的支持图片文件作为全屏状态候选

#### Scenario: 非法状态配置被拒绝
- **WHEN** 配置文档引用未知区域、空状态组、空搜索列表或逃逸出 `assets/` 的图片路径
- **THEN** 系统拒绝该配置并返回清晰错误

### Requirement: 界面状态循环探测维护会话统计
系统 SHALL 在后台界面状态循环探测期间维护会话级统计。统计 MUST 至少包含已完成探测轮数、最近一轮总耗时、每个已命中状态的命中次数，以及每个被早停跳过候选的跳过次数。统计 MUST 只基于已经完成的一轮探测结果更新。

#### Scenario: 探测轮次更新统计
- **WHEN** 后台界面状态探测完成一轮且当前状态为 `主页`
- **THEN** 会话统计中的总轮数增加 1
- **AND** `主页` 的命中次数增加 1
- **AND** 最近一轮耗时记录为该轮探测总耗时

#### Scenario: 未知状态不计入命中次数
- **WHEN** 后台界面状态探测完成一轮但当前状态为 `未知`
- **THEN** 会话统计中的总轮数增加 1
- **AND** 命中次数不为 `未知` 增加计数

#### Scenario: 记录早停跳过候选
- **WHEN** 后台界面状态探测结果中候选 `技能` 被标记为 skipped
- **THEN** 会话统计中的 `技能` 跳过次数增加 1

### Requirement: 界面状态配置可生成用户摘要
系统 SHALL 支持把 `assets/screen-states.json` 读取为用户可理解的只读配置摘要。摘要 MUST 包含每个状态组的状态名、搜索项名称、图片路径、搜索区域信息和最低置信度。缺少配置文件时，系统 MUST 返回空摘要而不是错误；配置非法时，系统 MUST 返回清晰错误。

#### Scenario: 配置摘要包含状态搜索项
- **WHEN** `assets/screen-states.json` 声明状态 `主页`，并包含搜索项 `主页标识`
- **THEN** 配置摘要包含状态 `主页`
- **AND** 该状态下包含搜索项 `主页标识`、图片路径、区域信息和最低置信度

#### Scenario: 缺少配置时返回空摘要
- **WHEN** `assets/screen-states.json` 不存在
- **THEN** 配置摘要表示没有已配置状态
- **AND** 系统不把缺少配置视为错误

#### Scenario: 非法配置摘要返回错误
- **WHEN** `assets/screen-states.json` 引用不存在图片或非法区域
- **THEN** 系统返回非零摘要结果和清晰错误消息

### Requirement: 界面状态循环探测保留最近候选结果
系统 SHALL 在后台界面状态循环探测会话中保留最近一轮候选结果摘要。摘要 MUST 至少包含候选名称、结果状态、耗时毫秒和命中置信度；没有完成探测轮次时，候选结果摘要 MUST 为空。

#### Scenario: 完成探测后快照包含候选结果
- **WHEN** 后台界面状态探测完成一轮，候选 `主页` 命中且候选 `人物` 被早停跳过
- **THEN** 会话状态快照包含 `主页` 和 `人物` 的最近候选结果
- **AND** `主页` 的结果状态为命中
- **AND** `人物` 的结果状态为跳过

#### Scenario: 尚未完成探测时候选结果为空
- **WHEN** 后台界面状态探测会话刚启动但还没有完成任何一轮
- **THEN** 会话状态快照中的最近候选结果为空

### Requirement: 界面状态候选保留搜索项名称
系统 SHALL 在从状态组配置生成界面状态候选时保留搜索项名称。候选的状态名 MUST 继续表示可被脚本条件引用的界面状态；搜索项名称 MUST 作为候选标识补充信息随探测结果和会话候选摘要保留。

#### Scenario: 配置搜索项名称进入候选结果
- **WHEN** `assets/screen-states.json` 声明状态 `战斗失败`，并包含搜索项 `离开按钮`
- **THEN** 生成的界面状态候选状态名为 `战斗失败`
- **AND** 该候选的搜索项名称为 `离开按钮`

#### Scenario: 当前状态仍使用状态名
- **WHEN** 一轮探测中状态 `战斗失败` 的搜索项 `离开按钮` 命中
- **THEN** 探测结果的当前状态为 `战斗失败`
- **AND** 当前状态不包含搜索项名称

#### Scenario: 资产扫描候选没有搜索项名称
- **WHEN** 系统从 `assets/主页.png` 生成兼容候选
- **THEN** 该候选状态名为 `主页`
- **AND** 该候选没有搜索项名称

### Requirement: CLI 支持单次界面状态探测
系统 SHALL 提供 `star probe-state` 子命令，用于执行一轮界面状态探测并输出当前状态和候选结果。CLI MUST 复用 application 层状态探测用例，不得在入口层执行图片匹配或解释状态识别规则。

#### Scenario: 探测并输出当前状态
- **WHEN** 用户运行 `star probe-state`
- **THEN** CLI 执行一轮状态探测
- **AND** 输出当前状态、总耗时和候选项结果

#### Scenario: 指定最低置信度
- **WHEN** 用户运行 `star probe-state --min-confidence 0.75`
- **THEN** CLI 使用 `0.75` 作为本次状态探测最低置信度

#### Scenario: 配置错误
- **WHEN** 状态配置非法
- **AND** 用户运行 `star probe-state`
- **THEN** CLI 返回配置错误并把原因写入 stderr

#### Scenario: 探测运行失败
- **WHEN** 图像定位 adapter 不可用
- **AND** 用户运行 `star probe-state`
- **THEN** CLI 返回运行错误并把原因写入 stderr

### Requirement: CLI 单次界面状态探测支持 JSON 输出

系统 SHALL 支持用户通过 `star probe-state --json` 获取机器可读的一轮界面状态探测结果。JSON 输出 MUST 复用 application 层状态探测结果，不得在 CLI 入口层执行图片匹配或解释状态识别规则。

#### Scenario: 输出机器可读探测结果

- **WHEN** 用户运行 `star probe-state --json`
- **THEN** CLI 执行一轮状态探测
- **AND** stdout 输出 JSON object
- **AND** JSON 包含 `current_state`、`known`、`elapsed_ms` 和 `candidates`
- **AND** 每个候选包含 `name`、`search_name`、`status`、`elapsed_ms` 和 `confidence`

#### Scenario: JSON 输出保留最低置信度参数

- **WHEN** 用户运行 `star probe-state --json --min-confidence 0.75`
- **THEN** CLI 使用 `0.75` 作为本次状态探测最低置信度
- **AND** stdout 输出 JSON object

#### Scenario: JSON 候选状态使用稳定枚举

- **WHEN** 候选命中、未命中或被跳过
- **AND** 用户运行 `star probe-state --json`
- **THEN** 对应候选的 `status` 分别为 `matched`、`missed` 或 `skipped`

#### Scenario: JSON 模式下配置错误仍写入 stderr

- **WHEN** 状态配置非法
- **AND** 用户运行 `star probe-state --json`
- **THEN** CLI 返回配置错误并把原因写入 stderr
- **AND** stdout 不输出 JSON

### Requirement: CLI 提供界面状态截图诊断入口

系统 SHALL 提供命令行截图诊断入口，用于帮助用户调试界面状态识别素材和区域。CLI MUST 复用 application 层截图诊断用例，不得在入口层直接截图、绘制区域或解析状态配置。

#### Scenario: 保存当前屏幕截图

- **WHEN** 用户运行 `star capture-screen`
- **THEN** CLI 保存一张当前屏幕截图
- **AND** stdout 输出截图保存路径
- **AND** CLI 返回 application 层用例的退出码

#### Scenario: 保存状态识别区域诊断图

- **WHEN** 用户运行 `star capture-region-diagnostics`
- **THEN** CLI 保存一张带状态识别区域框的诊断截图
- **AND** stdout 输出诊断图保存路径
- **AND** CLI 返回 application 层用例的退出码

#### Scenario: 截图诊断失败

- **WHEN** 截图 adapter 不可用、截图权限缺失、状态配置非法或缺少命名区域
- **AND** 用户运行截图诊断命令
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因

### Requirement: CLI 提供界面状态命名区域裁剪导出

系统 SHALL 提供命令行区域裁剪导出入口，用于把当前屏幕中的状态识别命名区域保存为独立图片。裁剪导出 MUST 复用 application 层截图诊断用例和状态配置解析，不得在 CLI 入口层直接截图、裁剪或解析状态配置。

#### Scenario: 保存命名区域裁剪图

- **WHEN** 用户运行 `star capture-region-crops`
- **AND** `assets/screen-states.json` 配置了命名区域
- **THEN** CLI 为每个命名区域保存一张裁剪图
- **AND** stdout 输出每个裁剪图保存路径
- **AND** CLI 返回 application 层用例的退出码

#### Scenario: 区域裁剪导出失败

- **WHEN** 截图 adapter 不可用、屏幕尺寸不可用、状态配置非法、缺少状态配置或缺少命名区域
- **AND** 用户运行 `star capture-region-crops`
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因

### Requirement: 界面状态候选暴露最佳匹配置信度

系统 SHALL 在界面状态探测候选结果中暴露每个已执行候选的最佳匹配置信度和最佳匹配位置。候选未达到最低阈值时，系统 MUST 仍保留底层图像匹配得到的最佳分数和最佳位置；候选被跳过或无法执行匹配时，最佳置信度和最佳位置 MAY 为 `null`。状态选择规则 MUST 继续只根据是否达到最低阈值判断命中。

#### Scenario: 未命中候选保留最佳置信度

- **WHEN** 候选图片匹配得到最佳分数 `0.62`
- **AND** 该候选最低阈值为 `0.8`
- **THEN** 候选结果未命中
- **AND** 候选结果的 `best_confidence` 为 `0.62`

#### Scenario: 未命中候选保留最佳位置

- **WHEN** 候选图片匹配得到最佳位置 `left=10, top=20, width=30, height=40`
- **AND** 该候选最低阈值为 `0.8`
- **THEN** 候选结果未命中
- **AND** 候选结果的 `best_rect` 为该位置

#### Scenario: CLI JSON 输出最佳置信度

- **WHEN** 用户运行 `star probe-state --json`
- **THEN** 每个候选 JSON object 包含 `best_confidence`
- **AND** 每个候选 JSON object 包含 `best_rect`
- **AND** 未命中候选的 `confidence` 仍为 `null`

#### Scenario: CLI 文本输出最佳置信度

- **WHEN** 用户运行 `star probe-state`
- **THEN** 每个候选文本行包含最佳置信度
- **AND** 每个候选文本行包含最佳位置

### Requirement: CLI 导出界面探测诊断截图

系统 SHALL 提供 `star capture-probe-diagnostics` 子命令，用于执行一轮界面状态探测并保存带候选最佳匹配框的诊断截图。CLI MUST 复用 application 层用例，不得在入口层执行截图、绘图或图片匹配。

#### Scenario: 导出探测诊断截图

- **WHEN** 用户运行 `star capture-probe-diagnostics`
- **THEN** 系统执行一轮界面状态探测
- **AND** 系统保存一张诊断截图
- **AND** 诊断截图包含候选的最佳匹配位置
- **AND** CLI 输出保存路径和当前探测状态

#### Scenario: 传递最低置信度

- **WHEN** 用户运行 `star capture-probe-diagnostics --min-confidence 0.75`
- **THEN** 系统使用 `0.75` 作为本次状态探测默认最低置信度

#### Scenario: 探测诊断截图失败

- **WHEN** 截图能力、屏幕尺寸或状态探测不可用
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因

### Requirement: CLI 导出界面探测候选裁剪图

系统 SHALL 提供 `star capture-probe-crops` 子命令，用于执行一轮界面状态探测并把每个候选的最佳匹配位置导出为独立裁剪图。CLI MUST 复用 application 层用例，不得在入口层执行截图、裁剪或图片匹配。

#### Scenario: 导出候选裁剪图

- **WHEN** 用户运行 `star capture-probe-crops`
- **THEN** 系统执行一轮界面状态探测
- **AND** 系统保存每个有 `best_rect` 的候选裁剪图
- **AND** CLI 输出每个裁剪图保存路径

#### Scenario: 传递最低置信度

- **WHEN** 用户运行 `star capture-probe-crops --min-confidence 0.75`
- **THEN** 系统使用 `0.75` 作为本次状态探测默认最低置信度

#### Scenario: 没有可裁剪候选

- **WHEN** 本轮状态探测没有任何候选包含 `best_rect`
- **THEN** CLI 返回成功
- **AND** CLI 输出没有保存候选裁剪图

#### Scenario: 候选裁剪失败

- **WHEN** 截图能力、屏幕尺寸或状态探测不可用
- **THEN** CLI 返回非零退出码
- **AND** stderr 输出 application 层返回的错误原因
