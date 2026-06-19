## ADDED Requirements

### Requirement: 图像定位端口接收解析后的模板
系统 SHALL 在 portable 执行层解析图片别名，`ScreenImageLocator` 端口仍只接收 `ImageTemplate`、可选区域和最低置信度。

#### Scenario: 命名图片解析后调用端口
- **WHEN** 脚本使用命名图片进行图片存在判断或图片点击
- **THEN** 调用 `ScreenImageLocator` 时传入的是解析后的 `ImageTemplate`，而不是图片名称
