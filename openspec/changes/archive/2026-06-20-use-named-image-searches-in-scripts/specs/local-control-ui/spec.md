## ADDED Requirements

### Requirement: UI 脚本详情解析搜索别名图片依赖
本地控制 UI SHALL 在脚本详情中解析 `ImageExists(SearchRef(...))` 和 `ImageTarget(SearchRef(...))` 的图片依赖。解析成功时，结构化 `image_dependencies` MUST 包含搜索别名最终指向的图片路径，依赖检查 MUST 报告该图片文件是否可用；解析失败时，依赖检查 MUST 报告搜索别名缺失。

#### Scenario: 搜索别名图片依赖可用
- **WHEN** 选中脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **AND** 脚本资源目录把 `离开按钮` 解析到 `assets/离开.png`
- **AND** 图片文件存在且后缀受支持
- **THEN** 脚本详情 `image_dependencies` 包含 `assets/离开.png`
- **AND** 依赖检查展示该搜索别名图片依赖可用

#### Scenario: 搜索别名缺失
- **WHEN** 选中脚本包含 `ImageExists(SearchRef("缺失搜索"))`
- **AND** 脚本资源目录没有配置该搜索别名
- **THEN** 脚本详情依赖检查展示搜索别名未配置

#### Scenario: 搜索别名参与 dry-run 图片依赖
- **WHEN** 用户选择包含搜索别名图片目标的脚本
- **AND** 用户在 UI 中以 dry-run 模式运行该脚本
- **THEN** UI 请求中的 `dry_run_images` 包含搜索别名解析出的图片路径
