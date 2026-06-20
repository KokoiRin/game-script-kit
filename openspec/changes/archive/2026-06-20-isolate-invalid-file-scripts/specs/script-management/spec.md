## MODIFIED Requirements

### Requirement: 加载项目文件脚本

系统 SHALL 从项目脚本目录加载用户可编辑的 JSON 脚本文件，并把合法脚本合并到可按名称查询的脚本 catalog 中。系统 MUST 保留内置脚本。系统 MUST 隔离坏文件脚本和重复名称文件脚本，使可用脚本仍然可列出和运行；系统 MUST 为被跳过的文件脚本提供可读配置错误。

#### Scenario: 列出文件脚本
- **WHEN** 项目脚本目录中存在合法脚本文件 `scripts/打图.json`
- **AND** 用户运行 `star list`
- **THEN** 输出包含脚本名 `打图`

#### Scenario: 内置脚本仍然可用
- **WHEN** 项目脚本目录不存在
- **AND** 用户运行 `star list`
- **THEN** 输出仍然包含内置脚本

#### Scenario: 隔离坏脚本文件
- **WHEN** 项目脚本目录中同时存在一个合法脚本文件和一个格式错误的脚本文件
- **AND** 用户运行 `star list`
- **THEN** 输出包含合法脚本名称
- **AND** 系统展示格式错误脚本文件的配置错误

#### Scenario: 隔离重复脚本名称
- **WHEN** 文件脚本名称和内置脚本或另一个文件脚本重复
- **THEN** 系统保留先出现的脚本
- **AND** 系统展示重复名称脚本文件的配置错误

## ADDED Requirements

### Requirement: CLI 展示文件脚本配置错误

系统 SHALL 在 `star list` 中保留 stdout 的可用脚本名称列表，并将项目文件脚本配置错误写入 stderr。配置错误 MUST 包含脚本文件名和可读原因。

#### Scenario: list 展示配置错误
- **WHEN** 项目脚本目录中存在坏脚本文件
- **AND** 用户运行 `star list`
- **THEN** stdout 仍包含可用脚本名称
- **AND** stderr 包含坏脚本文件名和错误原因
