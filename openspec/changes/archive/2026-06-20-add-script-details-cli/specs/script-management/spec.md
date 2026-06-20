## ADDED Requirements

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
