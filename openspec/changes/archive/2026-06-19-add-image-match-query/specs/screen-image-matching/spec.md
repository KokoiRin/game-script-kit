## ADDED Requirements

### Requirement: 未找到图片是查询结果
系统 SHALL 把满足依赖和截图条件但没有找到模板的情况表达为图片匹配查询的未找到结果，而不是平台 setup 错误。

#### Scenario: 查询层收到 None
- **WHEN** `ScreenImageLocator` 返回 `None`
- **THEN** 查询层会返回 found 为假的结果
