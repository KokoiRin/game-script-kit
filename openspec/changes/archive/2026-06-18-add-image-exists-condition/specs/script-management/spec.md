## ADDED Requirements

### Requirement: CLI dry-run 支持图片条件脚本
系统 SHALL 允许用户通过 `star run <name> --dry-run` 验证包含图片存在条件的脚本。dry-run 模式 MUST 使用可预测的图像定位实现，而不读取真实屏幕。

#### Scenario: dry-run 默认图片不存在
- **WHEN** 用户通过 `star run <name> --dry-run` 运行图片条件脚本且未指定 dry-run 图片
- **THEN** 系统会使用默认未找到结果评估图片条件，并打印对应计划操作或等待超时结果

#### Scenario: dry-run 指定图片存在
- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-image <template-path>` 运行图片条件脚本
- **THEN** 系统会对指定模板返回预设匹配结果，并按图片条件满足路径打印计划操作

#### Scenario: 默认 catalog 包含图片等待示例脚本
- **WHEN** 用户列出默认脚本
- **THEN** 结果中包含一个可用于验证 `WaitUntil(ImageExists(...))` 的示例脚本

### Requirement: CLI 真实运行注入图像定位 adapter
系统 SHALL 在真实运行包含图片存在条件的脚本时注入桌面图像定位 adapter，使 runner 可以通过 `ScreenImageLocator` 端口评估图片条件。

#### Scenario: macOS 模式运行图片条件脚本
- **WHEN** 用户通过 `star run <name>` 运行图片条件脚本
- **THEN** 系统会同时加载输入设备 adapter 和图像定位 adapter，并把它们注入 ScriptRunner

#### Scenario: 图像定位 adapter setup 失败被报告
- **WHEN** 真实运行时图像定位 adapter 因依赖、模板路径、权限或运行环境不可用而初始化或匹配失败
- **THEN** CLI 会返回非零退出码，并向用户报告脚本运行 setup 或运行失败

### Requirement: CLI dry-run 支持图片条件等待示例脚本
系统 SHALL 提供一个默认注册的图片条件等待示例脚本，使用户可以通过 `star run <name> --dry-run` 验证 `WaitUntil(ImageExists(...))` 的成功和超时路径。

#### Scenario: dry-run 验证图片条件等待成功路径
- **WHEN** 用户通过 `star run <name> --dry-run --dry-run-image <template-path>` 提供满足条件的模板图片路径
- **THEN** 系统会立即通过图片条件等待，并打印后续计划操作

#### Scenario: dry-run 验证图片条件等待超时路径
- **WHEN** 用户通过 `star run <name> --dry-run` 使用默认未找到结果
- **THEN** 系统会按等待间隔打印计划等待操作，并以非零退出码报告条件等待超时
