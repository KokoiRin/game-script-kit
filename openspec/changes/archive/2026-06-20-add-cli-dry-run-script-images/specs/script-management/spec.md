## ADDED Requirements

### Requirement: CLI dry-run 可自动使用脚本图片依赖
系统 SHALL 允许用户通过 `star run <name> --dry-run --dry-run-script-images` 自动把脚本详情解析出的图片依赖作为 dry-run 命中图片。该能力 MUST 复用 application 层脚本详情生成的 `image_dependencies`，不得在 CLI 入口层解释脚本步骤语义。

#### Scenario: 自动 dry-run 图片目标点击
- **WHEN** 命名脚本包含 `Click(ImageTarget(ImageTemplate("assets/start.png")))`
- **AND** 用户运行 `star run <name> --dry-run --dry-run-script-images`
- **THEN** CLI 把 `assets/start.png` 作为 dry-run 命中图片并打印点击输出

#### Scenario: 自动 dry-run 搜索别名图片目标
- **WHEN** `assets/screen-states.json` 配置搜索 `离开按钮`
- **AND** 命名脚本包含 `Click(ImageTarget(SearchRef("离开按钮")))`
- **AND** 用户运行 `star run <name> --dry-run --dry-run-script-images`
- **THEN** CLI 把搜索别名解析出的图片路径作为 dry-run 命中图片并打印点击输出

#### Scenario: 默认 dry-run 不自动命中图片
- **WHEN** 用户运行图片目标脚本且只提供 `--dry-run`
- **THEN** CLI 继续按图片未找到路径返回非零结果

#### Scenario: 非 dry-run 拒绝自动图片依赖开关
- **WHEN** 用户运行 `star run <name> --dry-run-script-images` 但没有提供 `--dry-run`
- **THEN** CLI 返回配置错误且不运行脚本
