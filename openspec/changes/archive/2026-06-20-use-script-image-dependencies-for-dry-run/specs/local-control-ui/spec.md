## ADDED Requirements

### Requirement: UI dry-run 使用脚本图片依赖
本地控制 UI SHALL 从脚本详情接口获取结构化图片依赖，并在 dry-run 运行当前脚本时把这些图片依赖作为 dry-run 图片命中模板提交给 application 层。HTTP adapter MUST 只转发前端提交的图片依赖列表，不得解析脚本展示文案；application 层 MUST 只在 dry-run 模式下把该列表传给脚本运行用例。

#### Scenario: 图片目标脚本 dry-run 成功
- **WHEN** 用户选择包含 `Click(ImageTarget(ImageTemplate("assets/start.png")))` 的脚本
- **AND** 用户在 UI 中以 dry-run 模式运行该脚本
- **THEN** UI 请求包含 `dry_run_images` 中的 `assets/start.png`
- **AND** application 层使用该图片作为 dry-run 命中模板
- **AND** 脚本按图片目标命中路径执行

#### Scenario: 真实运行忽略 dry-run 图片依赖
- **WHEN** 用户选择包含图片依赖的脚本
- **AND** 用户在 UI 中以真实运行模式运行该脚本
- **THEN** application 层不把 UI 提交的图片依赖作为 dry-run 命中模板
- **AND** 脚本继续通过真实桌面图像定位 adapter 查找图片

#### Scenario: 脚本详情接口返回结构化图片依赖
- **WHEN** UI 请求包含 `ImageExists(ImageTemplate("assets/start.png"))` 的脚本详情
- **THEN** HTTP 响应包含结构化字段 `image_dependencies`
- **AND** `image_dependencies` 包含 `assets/start.png`
