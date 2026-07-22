# target-application-activation Specification

## Purpose
定义真实脚本运行前激活目标应用的入口、应用层顺序、平台接入和失败行为，使自动化任务无需人工切换前台应用。

## Requirements
### Requirement: 真实脚本运行前可激活目标应用

系统 SHALL 允许调用方为真实脚本运行指定目标应用。应用层 MUST 在创建 runner 和执行任何输入动作前通过注入的 port 激活目标应用。

#### Scenario: 激活后运行脚本
- **WHEN** 调用方以真实模式运行脚本并指定目标应用
- **THEN** 系统先激活目标应用
- **AND** 激活成功后才创建 runner 并执行脚本

#### Scenario: 未指定目标应用
- **WHEN** 调用方以真实模式运行脚本且未指定目标应用
- **THEN** 系统保持现有运行行为
- **AND** 不要求应用激活 port

### Requirement: 激活失败阻止输入动作

系统 SHALL 把目标应用激活失败归一化为脚本 setup failure。失败后 MUST 不创建真实输入 device，也不得执行脚本动作。

#### Scenario: 目标应用不存在
- **WHEN** 平台无法激活用户指定的目标应用
- **THEN** 脚本结果退出码为 `1`
- **AND** 结束原因为 `setup_failed`
- **AND** 错误信息说明目标应用激活失败

### Requirement: dry-run 保持无目标应用副作用

系统 SHALL 保证 dry-run 不调用目标应用激活 port。CLI MUST 拒绝同时使用 `--dry-run` 和 `--target-app`。

#### Scenario: dry-run 参数冲突
- **WHEN** 用户运行 `star run` 或 `star run-plan` 并同时传入 `--dry-run` 和 `--target-app`
- **THEN** CLI 返回退出码 `2`
- **AND** 输出参数冲突说明

### Requirement: macOS 通过平台 adapter 激活应用

macOS adapter SHALL 使用系统应用启动能力按名称激活目标应用，并在成功后等待短暂稳定时间。平台命令错误 MUST 转换为 adapter 级 `RuntimeError`。

#### Scenario: 系统成功激活应用
- **WHEN** 系统应用启动命令成功返回
- **THEN** adapter 等待配置的稳定时间后返回

#### Scenario: 系统拒绝激活应用
- **WHEN** 系统命令返回非零状态或无法执行
- **THEN** adapter 抛出说明应用名和检查方向的 `RuntimeError`

### Requirement: Run Plan 为每个脚本恢复目标应用

系统 SHALL 在 Run Plan 的每个真实脚本项开始前激活同一个目标应用。

#### Scenario: 连续运行两个脚本
- **WHEN** 用户以真实模式和目标应用运行包含两个脚本的 Run Plan
- **THEN** 每个脚本项开始前各请求一次目标应用激活
