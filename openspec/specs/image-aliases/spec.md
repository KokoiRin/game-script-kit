# image-aliases Specification

## Purpose
TBD - created by archiving change add-image-aliases. Update Purpose after archive.
## Requirements
### Requirement: 脚本支持命名图片
系统 SHALL 提供平台无关的命名图片模型，使脚本可以通过稳定名称引用 `ImageTemplate`。命名图片 MUST 保留名称和值，并拒绝空名称。

#### Scenario: 创建命名图片
- **WHEN** 调用方使用名称 `开始按钮` 和 `ImageTemplate("assets/start.png")` 创建命名图片
- **THEN** 系统会保留该名称和值，并允许脚本把该名称解析为对应模板

#### Scenario: 空图片名称被拒绝
- **WHEN** 调用方使用空字符串或只包含空白字符的名称创建命名图片
- **THEN** 系统会拒绝该图片并报告名称不能为空

#### Scenario: 未知图片名称报错
- **WHEN** 脚本解析未注册的图片名称
- **THEN** 系统会拒绝解析并报告未知图片名称

