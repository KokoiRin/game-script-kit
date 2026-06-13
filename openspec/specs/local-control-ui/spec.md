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

#### Scenario: 脚本运行失败

- **WHEN** 脚本运行返回非零退出码或错误消息
- **THEN** UI 展示非零退出码和错误消息

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
