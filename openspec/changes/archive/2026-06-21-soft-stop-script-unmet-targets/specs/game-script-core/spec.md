## MODIFIED Requirements

### Requirement: ScriptRunner 执行条件等待步骤

引擎层 `ScriptRunner` SHALL 解释 `WaitUntil` 条件等待步骤，在条件满足前按轮询间隔等待，并在超时前条件变为真时继续执行后续步骤。若条件在超时时间内始终不满足，runner SHALL 正常停止本轮脚本并避免执行后续步骤。runner MUST 通过条件评估模块评估条件，并通过 `InputDevice.wait()` 表达等待。

#### Scenario: 条件等待超时

- **WHEN** ScriptRunner 执行 `WaitUntil` 且条件在超时时间内始终为假
- **THEN** 它会正常停止本轮脚本
- **AND** 它不会执行后续脚本步骤
- **AND** 它会输出条件等待未满足的运行事件

### Requirement: ScriptRunner 执行图片目标点击

引擎层 `ScriptRunner` SHALL 支持执行 `Click(ImageTarget(...))`。runner MUST 通过 `ScreenImageLocator` 端口解析图片目标，并在得到最终屏幕坐标后继续通过 `InputDevice.click()` 执行点击。若图片目标未定位到，runner SHALL 正常停止本轮脚本，不执行该点击和后续步骤。

#### Scenario: 图片目标未找到时正常停止

- **WHEN** `ScreenImageLocator` 对 `ImageTarget.template` 返回 `None`
- **THEN** runner 不会执行该点击
- **AND** runner 会正常停止本轮脚本
- **AND** runner 会输出图片目标未找到的运行事件
