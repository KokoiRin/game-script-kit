## MODIFIED Requirements

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
- **THEN** 用户可以通过通用脚本运行入口按名称启动该脚本

### Requirement: CLI 支持按名称启动脚本

系统 SHALL 提供命令行入口（`script_cli.py`），允许用户通过脚本名称选择并启动脚本。

#### Scenario: dry-run 指定脚本

- **WHEN** 用户通过 CLI 使用已存在的脚本名称和 dry-run 模式运行脚本
- **THEN** 系统会使用 `DryRunInputDevice` 按该脚本的动作顺序打印计划执行的操作，而不移动真实鼠标

#### Scenario: macOS 模式指定脚本

- **WHEN** 用户通过 CLI 使用已存在的脚本名称和 macOS 模式运行脚本
- **THEN** 系统会加载 macOS `InputDevice` adapter 并执行该脚本

#### Scenario: CLI 报告未知脚本

- **WHEN** 用户通过 CLI 指定不存在的脚本名称
- **THEN** 系统会返回非零退出码，并提示该脚本不存在
