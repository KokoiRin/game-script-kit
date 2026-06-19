## Context

当前 `ScreenImageLocator.locate(...)` 是单图定位端口。`PyAutoGuiScreenImageLocator.locate(...)` 内部完成截图、模板读取和 OpenCV 匹配，因此状态探测如果有 5 个候选，就会做 5 次截图。用户想要的是“截到一张图之后，跟很多素材进行匹配”，所以需要在 adapter seam 上表达批量定位能力，而不是在 UI 或 application 层缓存截图。

## Goals / Non-Goals

**Goals:**
- 为批量模板匹配新增独立 port，不破坏现有单图脚本条件和图片点击能力。
- desktop adapter 的 `locate_many(...)` 在一次调用中只截一次屏，并对所有模板复用同一张截图。
- 界面状态探测优先使用 batch locator，返回结果仍保持现有 `ScreenStateProbeResult`。
- 保留单图 fallback，避免没有 batch adapter 的测试替身或未来平台立即失效。

**Non-Goals:**
- 不做窗口区域选择。
- 不做模板缓存、图像金字塔、多尺度匹配或并行 OpenCV。
- 不改变 UI 控件和 HTTP API。
- 不改变 `ImageExists(...)` 或 `Click(ImageTarget(...))` 的单图语义。

## Decisions

1. **新增 `ScreenImageBatchLocator` 而不是修改 `ScreenImageLocator.locate`。**
   - 理由：单图定位已经被脚本条件、点击目标和测试替身使用；新增 port 可以让界面探测选择 batch 能力，同时不强迫所有现有 fake 一次性实现新方法。
   - 替代方案：给 `ScreenImageLocator` 增加 `locate_many` 必填方法。暂不采用，因为会扩大无关测试和 adapter 的改动面。

2. **batch 结果按输入模板顺序返回。**
   - 理由：状态探测已有候选顺序，按顺序 zip 即可汇总，无需引入字典键和路径规范化问题。

3. **desktop adapter 复用现有 OpenCV helper。**
   - 理由：坐标缩放、区域裁剪和异常归一化已经在现有 adapter 中实现；batch 只改变截图和模块加载的复用方式。

4. **状态探测保留 fallback。**
   - 理由：核心目标的真实 UI 路径会注入 batch adapter；fallback 让部分单元测试和未来平台能够渐进迁移。

## Risks / Trade-offs

- batch port 增加一层接口复杂度 -> 限定只在状态探测中使用，不影响脚本 DSL。
- 批量匹配仍然会逐模板执行 OpenCV `matchTemplate` -> 这解决重复截图问题，但不解决 OpenCV 大图匹配本身较慢的问题。
- 日志格式会新增 batch 行 -> 保留现有单图日志，避免破坏旧脚本运行日志。
