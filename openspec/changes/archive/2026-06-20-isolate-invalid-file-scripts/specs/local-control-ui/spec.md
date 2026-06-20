## ADDED Requirements

### Requirement: UI 展示文件脚本配置错误

本地控制 UI SHALL 在脚本列表接口和页面中展示文件脚本配置错误。HTTP adapter MUST 通过 application 层获得配置错误，不得自行解析脚本文件。

#### Scenario: HTTP 返回文件脚本配置错误
- **WHEN** 项目脚本目录中存在坏脚本文件
- **AND** UI 请求 `/api/scripts`
- **THEN** 响应包含可用脚本列表
- **AND** 响应包含坏脚本文件的配置错误

#### Scenario: 页面展示文件脚本配置错误
- **WHEN** UI 加载脚本列表并收到文件脚本配置错误
- **THEN** 页面展示脚本配置错误
- **AND** 页面仍允许用户选择可用脚本
