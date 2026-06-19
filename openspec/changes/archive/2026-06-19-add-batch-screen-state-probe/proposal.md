## Why

第一版界面状态探测已经接入 UI，但一轮探测会对每个候选图片分别调用单图定位。真实桌面 adapter 每次单图定位都会截图，这不符合“截到一张图之后跟很多素材匹配”的目标，也会让候选图片越多越慢。

## What Changes

- 新增批量图片定位 port：调用方提供多张模板，adapter 在同一轮中返回每张模板的匹配结果。
- desktop OpenCV adapter 支持一次截图后匹配多个模板，并记录批量匹配阶段耗时。
- 界面状态探测优先使用批量定位能力，一轮探测只触发一次截图；缺少 batch adapter 时保留单图 fallback，方便测试和渐进装配。
- 不改变 UI 页面功能形态，不新增脚本 DSL。

## Capabilities

### New Capabilities
- 无

### Modified Capabilities
- `screen-image-matching`: 增加批量图片定位能力，要求同一批模板共享一次屏幕截图。
- `screen-state-probe`: 要求界面状态探测在可用时使用批量图片定位，避免一轮内重复截图。

## Impact

- 更新 `portable.engine.ports`，新增 batch locator Protocol。
- 更新桌面图片匹配 adapter，新增 `locate_many(...)`。
- 更新界面状态探测 engine/application/composition，让 UI 探测路径注入 batch locator。
- 增加测试覆盖 batch port 使用、desktop adapter 一次截图多模板、fallback 行为和现有 UI 探测不回归。
