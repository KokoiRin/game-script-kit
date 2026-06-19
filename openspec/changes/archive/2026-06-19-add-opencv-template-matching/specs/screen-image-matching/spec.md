## ADDED Requirements

### Requirement: 桌面 adapter 使用 OpenCV 置信度匹配

桌面图像定位 adapter SHALL use OpenCV-backed template matching so callers can
use `min_confidence` values lower than `1.0` without depending on exact pixel
matching.

#### Scenario: adapter 返回实际最高匹配分数
- **WHEN** adapter 在截图中找到分数大于等于 `min_confidence` 的模板
- **THEN** 它返回 `ImageMatch`，其中 `confidence` 等于 OpenCV 计算出的最高匹配分数

#### Scenario: 最高分低于最低置信度
- **WHEN** adapter 完成截图和模板匹配，但最高匹配分数低于 `min_confidence`
- **THEN** 它返回 `None`

#### Scenario: 模板大于搜索区域
- **WHEN** 模板图片尺寸大于当前截图或指定搜索区域
- **THEN** adapter 返回 `None`，而不是报告 setup 错误

#### Scenario: OpenCV 依赖不可用
- **WHEN** adapter 无法导入 OpenCV 或其数组依赖
- **THEN** 它报告清晰的依赖 setup 错误
