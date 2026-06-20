## ADDED Requirements

### Requirement: UI dry-run 图片依赖解析命名图片
本地控制 UI SHALL 在生成结构化图片依赖时解析脚本资源目录中的命名图片引用。对于 `ImageExists(ImageRef(...))` 或 `Click(ImageTarget(ImageRef(...)))`，application 层 MUST 使用脚本 `resources` 将命名图片解析为对应 `ImageTemplate` 路径，并把该路径纳入 `image_dependencies`，使 UI dry-run 可继续通过既有 `dry_run_images` 请求字段提供模拟命中模板。

#### Scenario: 命名图片目标脚本 dry-run 成功
- **WHEN** 用户选择包含 `Click(ImageTarget(ImageRef("离开")))` 的脚本
- **AND** 脚本资源目录把 `离开` 解析为 `ImageTemplate("assets/离开.png")`
- **AND** 用户在 UI 中以 dry-run 模式运行该脚本
- **THEN** UI 请求包含 `dry_run_images` 中的 `assets/离开.png`
- **AND** application 层使用该图片作为 dry-run 命中模板
- **AND** 脚本按命名图片目标命中路径执行

#### Scenario: 脚本详情接口返回命名图片依赖路径
- **WHEN** UI 请求包含 `ImageExists(ImageRef("离开"))` 的脚本详情
- **AND** 脚本资源目录把 `离开` 解析为 `ImageTemplate("assets/离开.png")`
- **THEN** HTTP 响应字段 `image_dependencies` 包含 `assets/离开.png`

#### Scenario: 未知命名图片不生成 dry-run 命中模板
- **WHEN** UI 请求包含未知 `ImageRef("缺失")` 的脚本详情
- **THEN** HTTP 响应字段 `image_dependencies` 不包含 `缺失`
- **AND** 系统不为该未知引用生成 dry-run 图片路径
