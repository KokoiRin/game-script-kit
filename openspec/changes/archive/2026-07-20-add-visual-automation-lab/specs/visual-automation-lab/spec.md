## ADDED Requirements

### Requirement: 独立启动视觉自动化靶场

系统 SHALL 提供独立 `star-lab` 命令，在本地启动视觉自动化目标页面。靶场 MUST 不导入或调用 Star 的脚本 domain、runner、application 或平台 adapter。

#### Scenario: 启动靶场
- **WHEN** 用户运行 `star-lab --no-open`
- **THEN** 系统启动本地 HTTP 服务并输出访问地址
- **AND** 不自动打开浏览器窗口

#### Scenario: 默认打开浏览器
- **WHEN** 用户运行 `star-lab`
- **THEN** 系统启动本地 HTTP 服务并在浏览器打开目标页面

### Requirement: 任务处理台使用确定状态机

靶场 SHALL 提供固定“任务处理台”场景，按 `home`、`task_list`、`loading`、`confirm`、`completed` 状态转换。系统 MUST 拒绝当前状态不允许的动作，并且不得静默改变状态。

#### Scenario: 完成正常任务流程
- **WHEN** 调用方依次执行 `open_tasks`、`select_target`，等待加载到期后执行 `confirm_task`
- **THEN** 场景最终状态为 `completed`

#### Scenario: 拒绝非法动作
- **WHEN** 调用方在 `home` 状态执行 `confirm_task`
- **THEN** 系统拒绝该动作
- **AND** 状态仍为 `home`

### Requirement: 页面通过视觉目标暴露状态

靶场页面 SHALL 根据服务端状态展示固定、高对比且可点击的视觉目标。页面 MUST 通过目标应用自身的 HTTP 动作接口提交点击，并根据状态接口更新可见内容。

#### Scenario: 任务列表展示目标
- **WHEN** 场景处于 `task_list` 且模式不是 `missing_target`
- **THEN** 页面展示可点击的目标任务图片

#### Scenario: 完成页展示完成标识
- **WHEN** 场景状态为 `completed`
- **THEN** 页面展示稳定的完成标识

### Requirement: 提供独立真值接口

靶场 SHALL 提供 JSON 状态、事件和重置接口，供测试程序在不依赖 Star 自报结果的情况下验收。状态响应 MUST 包含当前状态、模式、序号和允许动作；事件响应 MUST 按序保留重置、用户动作和自动转换。

#### Scenario: 查询状态
- **WHEN** 测试程序请求 `/api/state`
- **THEN** 响应包含当前状态、模式、序号和允许动作

#### Scenario: 查询事件
- **WHEN** 测试程序请求 `/api/events`
- **THEN** 响应按发生顺序返回场景事件

#### Scenario: 重置场景
- **WHEN** 测试程序向 `/api/reset` 提交合法模式和加载延迟
- **THEN** 场景回到 `home`
- **AND** 新的重置事件成为当前事件序列起点

### Requirement: 支持可重复故障模式

靶场 SHALL 支持 `normal`、`slow` 和 `missing_target` 模式。`slow` MUST 延长加载状态；`missing_target` MUST 隐藏目标任务并拒绝 `select_target`。

#### Scenario: 慢加载
- **WHEN** 场景以 `slow` 模式选择目标任务
- **THEN** 状态在配置的加载期限内保持 `loading`
- **AND** 期限到达后转换为 `confirm`

#### Scenario: 目标缺失
- **WHEN** 场景以 `missing_target` 模式进入任务列表
- **THEN** 允许动作不包含 `select_target`
- **AND** 页面不展示目标任务图片
