## ADDED Requirements

### Requirement: CLI dry-run 支持图片目标点击脚本
系统 SHALL 允许用户通过 `star run <name> --dry-run --dry-run-image <template-path>` 验证包含图片目标点击的脚本。dry-run 模式 MUST 使用可预测的图像定位实现，而不读取真实屏幕。

#### Scenario: dry-run 图片目标点击成功
- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-image <template-path>` 运行图片目标点击脚本
- **THEN** 系统会对指定模板返回预设匹配结果，并打印解析后的点击坐标

#### Scenario: dry-run 图片目标点击未找到
- **WHEN** 用户通过 `star run <name> --dry-run` 运行图片目标点击脚本且未指定 dry-run 图片
- **THEN** 系统会返回非零退出码，并报告图片目标未找到

#### Scenario: 默认 catalog 包含图片目标点击示例脚本
- **WHEN** 用户列出默认脚本
- **THEN** 结果中包含一个可用于验证 `Click(ImageTarget(...))` 的示例脚本

### Requirement: CLI 真实运行注入图片目标点击所需 adapter
系统 SHALL 在真实运行包含图片目标点击的脚本时注入桌面图像定位 adapter，使 runner 可以通过 `ScreenImageLocator` 端口解析点击坐标。

#### Scenario: macOS 模式运行图片目标点击脚本
- **WHEN** 用户通过 `star run <name>` 运行图片目标点击脚本
- **THEN** 系统会同时加载输入设备 adapter 和图像定位 adapter，并把它们注入 ScriptRunner

#### Scenario: 图片目标点击运行失败被报告
- **WHEN** 真实运行时图像定位 adapter 因依赖、模板路径、权限、未找到图片或运行环境不可用而失败
- **THEN** CLI 会返回非零退出码，并向用户报告脚本运行失败
