## ADDED Requirements

### Requirement: UI 图片点击支持最低匹配置信度

本地控制 UI SHALL allow image-click requests to provide a minimum match
confidence, so real image clicks can use OpenCV fuzzy matching instead of exact
pixel matching.

#### Scenario: HTTP 图片点击请求传递最低置信度
- **WHEN** 浏览器调用 `/api/click-image` 并提供 `min_confidence`
- **THEN** HTTP adapter 会把该值传给 application 层图片点击用例

#### Scenario: application 用最低置信度构造图片目标
- **WHEN** application 层运行图片点击用例
- **THEN** 它使用请求中的最低置信度构造 `ImageTarget`

#### Scenario: 非法最低置信度
- **WHEN** 图片点击请求提供小于等于 0 或大于 1 的最低置信度
- **THEN** application 层拒绝请求并返回配置错误
