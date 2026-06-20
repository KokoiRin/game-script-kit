## ADDED Requirements

### Requirement: UI 依赖检查解析命名图片
本地控制 UI SHALL 在脚本详情依赖检查中解析脚本资源目录里的命名图片。对于 `ImageExists(ImageRef(...))` 或 `Click(ImageTarget(ImageRef(...)))`，application 层 MUST 使用脚本 `resources` 判断该命名图片是否已配置，并在已配置时继续检查解析后的 `ImageTemplate` 路径是否位于项目 `assets/` 目录且后缀受支持。

#### Scenario: 命名图片依赖可用
- **WHEN** 选中脚本依赖命名图片 `ImageRef("离开")`
- **AND** 脚本资源目录把 `离开` 解析为 `ImageTemplate("assets/离开.png")`
- **AND** `assets/离开.png` 文件存在且后缀受支持
- **THEN** 脚本详情展示该命名图片依赖状态为可用

#### Scenario: 命名图片文件缺失
- **WHEN** 选中脚本依赖命名图片 `ImageRef("离开")`
- **AND** 脚本资源目录把 `离开` 解析为 `ImageTemplate("assets/离开.png")`
- **AND** `assets/离开.png` 文件不存在
- **THEN** 脚本详情展示该命名图片依赖状态为缺失

#### Scenario: 命名图片未配置
- **WHEN** 选中脚本依赖命名图片 `ImageRef("缺失")`
- **AND** 脚本资源目录没有配置 `缺失`
- **THEN** 脚本详情展示该命名图片依赖状态为缺失
- **AND** 页面消息说明命名图片未配置
