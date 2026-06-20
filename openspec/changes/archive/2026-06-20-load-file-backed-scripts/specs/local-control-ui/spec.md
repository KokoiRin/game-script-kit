## ADDED Requirements

### Requirement: UI 识别项目文件脚本

本地控制 UI SHALL 识别项目脚本目录中的文件脚本，并在脚本列表、脚本详情和运行入口中把文件脚本当作普通命名脚本处理。HTTP adapter MUST 通过 application 层获得脚本 catalog，不得自行解析脚本文件。

#### Scenario: UI 列出文件脚本
- **WHEN** 项目脚本目录中存在合法文件脚本
- **AND** UI 请求 `/api/scripts`
- **THEN** 响应包含该文件脚本名称

#### Scenario: UI 展示文件脚本详情
- **WHEN** UI 请求文件脚本的 `/api/script-details`
- **THEN** 响应包含该文件脚本的步骤和依赖摘要

#### Scenario: UI 运行文件脚本
- **WHEN** UI 调用 `/api/run-script` 运行文件脚本
- **THEN** application 按该文件脚本执行并返回运行状态
