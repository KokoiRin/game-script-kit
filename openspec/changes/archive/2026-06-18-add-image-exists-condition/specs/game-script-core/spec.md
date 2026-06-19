## ADDED Requirements

### Requirement: ScriptRunner 评估图片存在条件
引擎层 `ScriptRunner` SHALL 支持通过 `ScreenImageLocator` 端口评估 `ImageExists` 条件。runner MUST 保持平台无关，不得直接导入或初始化桌面图像匹配 adapter。

#### Scenario: 图片存在条件为真
- **WHEN** `ScreenImageLocator` 对 `ImageExists.template` 返回满足最低置信度的 `ImageMatch`
- **THEN** 条件评估结果为真

#### Scenario: 图片存在条件为假
- **WHEN** `ScreenImageLocator` 对 `ImageExists.template` 返回 `None`
- **THEN** 条件评估结果为假

#### Scenario: 图片存在条件解析搜索区域
- **WHEN** ScriptRunner 在绑定区域窗口的脚本内评估带 `region` 的 `ImageExists`
- **THEN** 条件评估模块会先使用脚本窗口解析搜索区域左上角，再把解析后的屏幕区域交给图像定位端口

#### Scenario: 图片存在条件传递最低匹配置信度
- **WHEN** ScriptRunner 评估带最低匹配置信度的 `ImageExists`
- **THEN** 条件评估模块会把该最低匹配置信度传给 `ScreenImageLocator`

#### Scenario: 缺少图像定位端口时报错
- **WHEN** ScriptRunner 执行包含图片存在条件的脚本但未注入图像定位端口
- **THEN** 它会拒绝执行该条件并报告图像定位端口缺失

#### Scenario: 条件分支使用图片存在条件
- **WHEN** ScriptRunner 执行图片存在条件结果为真的 `If`
- **THEN** 它会按现有条件分支语义执行 `then_steps`

#### Scenario: 条件等待使用图片存在条件
- **WHEN** ScriptRunner 执行图片存在条件初始为假但在超时前变为真的 `WaitUntil`
- **THEN** 它会按现有条件等待语义轮询并在条件满足后继续执行后续步骤
