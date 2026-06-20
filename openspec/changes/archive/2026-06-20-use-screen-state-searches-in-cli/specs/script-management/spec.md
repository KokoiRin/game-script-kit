## ADDED Requirements

### Requirement: CLI 脚本复用状态配置搜索别名
系统 SHALL 允许 `star run` 运行的命名脚本复用 `assets/screen-states.json` 中配置的搜索别名。CLI MUST 在调用脚本运行用例前把状态配置中的搜索项作为共享脚本资源注入；脚本自身资源 MUST 覆盖共享资源中的同名资源。

#### Scenario: dry-run 运行状态配置搜索别名脚本
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮` 并指向 `assets/离开.png`
- **AND** 命名脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **AND** 用户运行 `star run <name> --dry-run --dry-run-image <assets/离开.png>`
- **THEN** CLI 使用状态配置中的搜索别名解析图片目标并打印 dry-run 点击输出

#### Scenario: 缺少状态配置不影响普通脚本
- **WHEN** 项目没有 `assets/screen-states.json`
- **AND** 用户运行不依赖搜索别名的命名脚本
- **THEN** CLI 继续按原有方式运行脚本

#### Scenario: 脚本资源覆盖共享搜索别名
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮` 指向 `assets/配置.png`
- **AND** 脚本自身资源也配置搜索 `离开按钮` 指向 `assets/脚本.png`
- **THEN** CLI 使用脚本自身资源中的搜索定义
