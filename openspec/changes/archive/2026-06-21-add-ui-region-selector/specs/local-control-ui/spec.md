## ADDED Requirements

### Requirement: UI 生成截屏诊断

本地控制 UI SHALL 提供截屏诊断入口，用于保存一张当前屏幕截图并在页面中展示。截图响应 SHOULD 包含截图像素尺寸和屏幕坐标尺寸，使页面可以把用户在截图预览上选择的区域换算为脚本可用坐标。HTTP adapter MUST 只委托 application 层截图用例，不得直接访问平台截图 adapter。

#### Scenario: 截图响应包含坐标换算尺寸

- **WHEN** 用户点击截屏诊断按钮
- **THEN** UI 展示最近截图
- **AND** 响应包含截图像素尺寸
- **AND** 如果 screen size 能读取，响应包含屏幕坐标尺寸

### Requirement: UI 在截图预览上选择脚本区域

本地控制 UI SHALL 允许用户在最近一次截图预览上拖拽选择矩形区域。页面 MUST 根据截图显示尺寸、截图像素尺寸和屏幕坐标尺寸换算出脚本可用的 `left/top/width/height`。页面 MUST 展示可直接复制到 JSON 的区域片段。

#### Scenario: 拖拽选择区域并展示 JSON

- **GIVEN** 页面已经展示一张截图
- **WHEN** 用户在截图上从左上拖拽到右下
- **THEN** 页面展示换算后的 `left/top/width/height`
- **AND** 页面展示 JSON 区域片段

#### Scenario: 反向拖拽仍生成正向区域

- **GIVEN** 页面已经展示一张截图
- **WHEN** 用户在截图上从右下拖拽到左上
- **THEN** 页面仍展示正向宽高的区域坐标

### Requirement: UI 预览区域内图片匹配

本地控制 UI SHALL 允许用户使用当前选中的图片素材、最低置信度和截图选择区域执行一次只读图片匹配预览。预览 MUST NOT 点击鼠标。预览结果 MUST 展示是否命中、置信度、匹配矩形和日志摘要。

#### Scenario: 区域内图片命中

- **GIVEN** 用户已经选择截图区域和图片素材
- **WHEN** 用户点击区域匹配预览
- **THEN** HTTP adapter 把素材、最低置信度和区域传给 application
- **AND** UI 展示命中状态、置信度和匹配矩形

#### Scenario: 未选择区域时拒绝预览

- **GIVEN** 页面还没有有效截图选择区域
- **WHEN** 用户点击区域匹配预览
- **THEN** UI 不发送匹配请求
- **AND** 页面提示需要先选择区域
