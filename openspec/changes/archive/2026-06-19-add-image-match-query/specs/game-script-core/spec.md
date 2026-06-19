## ADDED Requirements

### Requirement: 条件和点击复用图片匹配查询
引擎层 SHALL 通过统一图片匹配查询层评估图片存在条件和解析图片点击目标。查询层 MUST 继续使用已注入的 `ScreenImageLocator`，不得创建平台 adapter。

#### Scenario: 图片存在条件消费查询结果
- **WHEN** 图片匹配查询返回 found 为真
- **THEN** 图片存在条件评估为真

#### Scenario: 图片目标点击消费查询结果
- **WHEN** 图片匹配查询返回 `ImageMatch`
- **THEN** 图片目标点击会继续使用匹配中心点作为点击点

#### Scenario: 图片目标未找到仍报错
- **WHEN** 图片匹配查询返回 found 为假
- **THEN** 图片目标点击会拒绝执行并报告图片目标未找到
