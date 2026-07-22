## ADDED Requirements

### Requirement: 真实运行可按标题锁定目标窗口

系统 SHALL 允许调用方在指定目标应用时同时指定顶层窗口标题子串。应用层 MUST 在创建 runner 前先激活应用，再选择并 Raise 唯一匹配窗口。

#### Scenario: 唯一窗口命中
- **WHEN** 目标应用存在唯一标题包含指定文本的可见顶层窗口
- **THEN** 系统 Raise 该窗口
- **AND** 使用该窗口当前屏幕矩形准备脚本

#### Scenario: 未指定窗口标题
- **WHEN** 调用方只指定目标应用而未指定窗口标题
- **THEN** 系统保持应用级激活行为
- **AND** 不要求窗口控制 port

### Requirement: 目标窗口成为本轮脚本坐标和图片边界

系统 SHALL 使用目标窗口矩形创建本轮脚本副本的 `AreaWindow`。原 catalog 脚本 MUST 不被修改。

#### Scenario: 窗口内点位
- **WHEN** 目标窗口左上角为 `(100, 200)` 且脚本点击点为 `(10, 20)`
- **THEN** 本轮点击屏幕坐标为 `(110, 220)`

#### Scenario: 图片目标未声明区域
- **WHEN** 绑定目标窗口的图片条件或图片目标未声明搜索区域
- **THEN** 图片搜索区域为目标窗口整体矩形

### Requirement: 窗口选择失败阻止输入动作

系统 SHALL 把窗口缺失、标题歧义和平台 Raise 失败归一化为 setup failure。失败后 MUST 不创建真实输入 device。

#### Scenario: 没有匹配窗口
- **WHEN** 目标应用没有标题匹配的可见顶层窗口
- **THEN** 脚本结果结束原因为 `setup_failed`
- **AND** 错误说明没有找到目标窗口

#### Scenario: 多个窗口匹配
- **WHEN** 同一应用存在多个标题匹配的顶层窗口
- **THEN** 脚本结果结束原因为 `setup_failed`
- **AND** 错误要求使用更具体的窗口标题

### Requirement: CLI 校验目标窗口参数

CLI SHALL 要求 `--target-window-title` 与 `--target-app` 一起使用，并保持 dry-run 无真实窗口副作用。

#### Scenario: 缺少目标应用
- **WHEN** 用户只传入 `--target-window-title`
- **THEN** CLI 返回退出码 `2`
- **AND** 不运行脚本

#### Scenario: dry-run 请求窗口锁定
- **WHEN** 用户同时使用 dry-run、目标应用和目标窗口标题
- **THEN** CLI 返回退出码 `2`
- **AND** 不调用真实窗口 port

### Requirement: Run Plan 为每个脚本重新解析窗口

系统 SHALL 在 Run Plan 每个真实脚本项开始前重新选择目标窗口和读取矩形。

#### Scenario: 两个脚本之间窗口移动
- **WHEN** Run Plan 的第二个脚本开始前目标窗口矩形发生变化
- **THEN** 第二个脚本使用重新读取的窗口矩形
