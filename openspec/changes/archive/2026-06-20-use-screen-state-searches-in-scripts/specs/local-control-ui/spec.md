## ADDED Requirements

### Requirement: UI 脚本可复用状态配置搜索别名
本地控制 application SHALL 允许 UI 运行和展示命名脚本时复用 `assets/screen-states.json` 中配置的搜索别名。系统 MUST 在进入脚本详情、同步运行或后台运行前把状态配置中的搜索项作为共享脚本资源注入；脚本自身资源 MUST 覆盖共享资源中的同名资源。

#### Scenario: 脚本详情解析状态配置搜索别名
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮` 并指向 `assets/离开.png`
- **AND** 脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **THEN** 脚本详情 `image_dependencies` 包含 `assets/离开.png`
- **AND** 依赖检查展示该搜索别名图片依赖可用

#### Scenario: dry-run 运行使用状态配置搜索别名
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮`
- **AND** 脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **AND** 用户以 dry-run 模式运行脚本
- **THEN** application 使用状态配置中的搜索别名解析图片目标

#### Scenario: 脚本资源覆盖共享搜索别名
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮` 指向 `assets/配置.png`
- **AND** 脚本自身资源也配置搜索 `离开按钮` 指向 `assets/脚本.png`
- **THEN** 脚本详情和运行均使用脚本自身资源中的 `assets/脚本.png`
