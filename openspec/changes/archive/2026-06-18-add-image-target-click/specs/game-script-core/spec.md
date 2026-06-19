## ADDED Requirements

### Requirement: ScriptRunner 执行图片目标点击
引擎层 `ScriptRunner` SHALL 支持执行 `Click(ImageTarget(...))`。runner MUST 通过 `ScreenImageLocator` 端口解析图片目标，并在得到最终屏幕坐标后继续通过 `InputDevice.click()` 执行点击。

#### Scenario: 图片目标点击匹配中心点
- **WHEN** `ScreenImageLocator` 对 `ImageTarget.template` 返回 `ImageMatch`
- **THEN** runner 会点击该匹配结果的中心点

#### Scenario: 图片目标点击应用 offset
- **WHEN** `ImageTarget` 设置了 offset
- **THEN** runner 会点击匹配中心点加 offset 后的屏幕坐标

#### Scenario: 图片目标点击解析搜索区域
- **WHEN** ScriptRunner 在绑定区域窗口的脚本内执行带 `region` 的 `Click(ImageTarget(...))`
- **THEN** runner 会先使用脚本窗口解析搜索区域左上角，再把解析后的屏幕区域交给图像定位端口

#### Scenario: 图片目标点击传递最低匹配置信度
- **WHEN** ScriptRunner 执行带最低匹配置信度的 `Click(ImageTarget(...))`
- **THEN** runner 会把该最低匹配置信度传给 `ScreenImageLocator`

#### Scenario: 图片目标未找到时报错
- **WHEN** `ScreenImageLocator` 对 `ImageTarget.template` 返回 `None`
- **THEN** runner 会拒绝执行该点击并报告图片目标未找到

#### Scenario: 缺少图像定位端口时报错
- **WHEN** ScriptRunner 执行 `Click(ImageTarget(...))` 但未注入图像定位端口
- **THEN** runner 会拒绝执行该点击并报告图像定位端口缺失

#### Scenario: 静态点点击行为保持不变
- **WHEN** ScriptRunner 执行 `Click(Point(...))`
- **THEN** runner 会继续按脚本窗口解析静态点并调用 `InputDevice.click()`
