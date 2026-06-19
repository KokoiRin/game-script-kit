## Context

当前脚本已经通过 `PixelColorReader` 支持单点取色，并通过 `ColorIs`、`If`、`WaitUntil` 把屏幕状态接入控制流。下一步要识别按钮、图标或状态块时，单点颜色过于脆弱，需要一个比颜色端口更高层、但仍然平台无关的屏幕图像匹配 seam。

现有架构要求核心规则保持可测试、可移植，真实截图、macOS 权限、平台库和图片加载细节必须留在外层 adapter。这个 change 只建立图像匹配端口和 macOS 可用的桌面 adapter；后续 change 再把该端口接入 `ImageExists(...)` 条件和按图片定位点击。

## Goals / Non-Goals

**Goals:**

- 定义平台无关的图像模板、搜索区域、匹配结果和值域不变量。
- 新增 `ScreenImageLocator` engine port，用于查找当前屏幕中的模板图像。
- 提供 macOS 本地运行可用的桌面 adapter，复用现有 `pyautogui` 截图能力并封装截图权限错误。
- 提供 fake/dry-run 友好的实现，使端口行为可以在无真实屏幕的测试环境中验证。
- 保持 `InputDevice` 只负责点击、拖拽和等待，不加入屏幕读取职责。

**Non-Goals:**

- 不新增 `ImageExists(...)`、`MultiPointColorIs(...)` 或任何脚本 DSL 条件。
- 不新增 `Click(ImageTarget(...))`、拖拽到图片、等待图片后点击等动作语义。
- 不承诺多匹配结果、排序、尺度变化、旋转匹配、OCR 或实时视频流识别。
- 不把平台依赖引入领域层、engine 层、scripts_manager 或测试替身。

## Decisions

### Decision 1: 新增独立 `ScreenImageLocator` port

端口形状建议为：

```python
class ScreenImageLocator(Protocol):
    def locate(
        self,
        template: ImageTemplate,
        *,
        region: Rect | None = None,
        min_confidence: float = 1.0,
    ) -> ImageMatch | None:
        """在当前屏幕或指定区域内查找模板图片。"""
```

`ImageTemplate` 表达模板图片来源，第一版使用本地文件路径或资源路径字符串；adapter 负责读取图片文件。`ImageMatch` 保存匹配矩形、中心点和置信度。返回 `None` 表示未找到，adapter setup/权限/图片无法读取等问题用清晰 `RuntimeError` 报告。

理由：

- 和 `PixelColorReader.read_color(point)` 一样，核心只依赖端口，不知道截图或图像库。
- `region` 留在端口参数里，后续 `ImageExists(..., region=...)` 和图片定位点击可以直接复用。
- `ImageMatch | None` 比抛异常表达“未找到”更适合条件判断和等待轮询。

备选方案：

- 让 `PixelColorReader` 扩展为屏幕读取端口。拒绝：会把单点取色和模板定位混在一个接口中，降低端口职责清晰度。
- 让 `InputDevice` 增加图像查找方法。拒绝：输入端口不应承担屏幕读取职责，和现有 spec 冲突。
- 直接在 `ImageExists` 条件中实现截图匹配。拒绝：会让领域/engine 语义过早依赖平台实现。

### Decision 2: 图像匹配模型放在领域层，匹配算法留在 adapter

新增值对象建议包括：

- `ImageTemplate(path: str)`：记录模板图片位置，拒绝空路径。
- `ImageMatch(rect: Rect, confidence: float)`：记录匹配区域和置信度，`center` 可作为只读属性由 `rect` 计算。
- `min_confidence` 校验范围为 `0.0 < min_confidence <= 1.0`。

理由：

- 模板来源、匹配矩形和置信度是脚本语义会复用的稳定概念。
- 文件读取、截图、图像解码和算法选择是 adapter 的变化点，不能进入领域模型。

### Decision 3: macOS 第一版复用 `pyautogui` 的屏幕定位能力

桌面 adapter 建议命名为 `PyAutoGuiScreenImageLocator`，放在 `platform/desktop/adapters/image_matching.py`，由 macOS/local desktop composition 注入。第一版通过延迟加载 `pyautogui`，调用其屏幕定位能力，并把 `Box`/tuple 结果转换为领域 `Rect` 和 `ImageMatch`。

依赖策略：

- `min_confidence == 1.0`：优先使用现有 `pyautogui` 能力，不新增依赖。
- `min_confidence < 1.0`：如果当前后端不支持 confidence 或缺少 OpenCV，adapter 抛出清晰 setup 错误，提示需要安装支持置信度匹配的依赖；是否把 OpenCV 加入正式依赖由实现时按测试和安装可用性确认。

理由：

- 项目当前已经依赖 `pyautogui`，且现有取色 adapter 也通过它截图。
- 把 OpenCV 作为第一步必需依赖会增加安装重量；端口先成型比算法完备更重要。
- adapter 报错比静默降级更安全，避免用户以为低置信度匹配已经生效。

### Decision 4: 第一版只返回一个匹配结果

`locate()` 返回最佳或后端定义的首个匹配，后续如需批量状态识别再引入 `locate_all()` 或多结果返回模型。

理由：

- 用户当前最需要的是“图片是否存在”和“图片中心点在哪里”。
- 单结果可以支撑 `ImageExists`、`WaitUntil(ImageExists)` 和 `Click(ImageTarget)` 的最小闭环。
- 多结果排序和去重规则容易牵涉算法细节，适合后续单独规格化。

## Risks / Trade-offs

- [Risk] macOS 截图权限不足会导致真实 adapter 不可用。→ Mitigation: adapter 捕获底层异常并报告检查 Screen Recording 权限，测试主体使用 fake 和注入后端。
- [Risk] Retina/缩放、主题变化或抗锯齿会让精确模板匹配不稳定。→ Mitigation: 第一版支持 `min_confidence` 参数和区域限制；后续可在同一端口后替换 OpenCV 后端。
- [Risk] 模板图片路径如果由脚本任意传入，可能让后续 CLI 暴露过宽文件读取面。→ Mitigation: 本 change 只建立端口；后续接入 CLI/脚本时再定义模板资产目录或白名单规则。
- [Risk] `pyautogui.locateOnScreen` 在大屏全屏搜索上可能较慢。→ Mitigation: 端口原生支持 `region`，README 和 demo 鼓励优先限制搜索区域。
