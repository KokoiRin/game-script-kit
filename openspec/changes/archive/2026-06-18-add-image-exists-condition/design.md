## Context

`add-screen-image-matching-port` 已经建立 `ImageTemplate`、`ImageMatch` 和 `ScreenImageLocator`，并提供了本地桌面 adapter 与 dry-run 替身。当前缺口是脚本条件仍然只有 `ColorIs(point)`，无法把图片存在性用于 `If` 或 `WaitUntil`。

这个 change 把图像匹配端口接入现有条件系统，但仍然保持 ports-and-adapters 边界：领域模型只保存 `ImageExists` 表达式，engine 通过注入的 `ScreenImageLocator` 评估条件，真实截图和匹配算法继续留在 desktop adapter。

## Goals / Non-Goals

**Goals:**

- 新增 `ImageExists(template, region=None, min_confidence=1.0)` 条件模型。
- 让 `condition_evaluator` 通过 `ScreenImageLocator` 判断图片条件是否成立。
- 让 `If(ImageExists(...))` 和 `WaitUntil(ImageExists(...))` 复用现有 runner 控制流语义。
- 扩展脚本需求分析、应用层和本地桌面 composition，按需注入 image locator。
- 扩展 dry-run，使图片条件脚本可以通过可预测的预设图片匹配结果验证。
- 新增命名 demo 脚本，提供用户可直接运行的 dry-run 成功和超时路径。

**Non-Goals:**

- 不实现 `Click(ImageTarget(...))` 或任何按图片定位点击动作。
- 不新增多图片条件、批量匹配、OCR、缩放/旋转匹配语义。
- 不新增真实图片资产管理白名单；模板路径仍只是领域模型中的字符串，后续脚本文件化时再收紧。
- 不改变 `ColorIs`、`If`、`WaitUntil` 的既有行为。

## Decisions

### Decision 1: `ImageExists` 是条件模型，不是动作或 adapter API

领域模型建议为：

```python
@dataclass(frozen=True, slots=True)
class ImageExists:
    template: ImageTemplate
    region: Rect | None = None
    min_confidence: float = 1.0
```

`Condition` 扩展为 `ColorIs | ImageExists`。`min_confidence` 使用和 `ScreenImageLocator.locate()` 一致的规则：`0.0 < min_confidence <= 1.0`。

理由：

- `ImageExists` 表达“屏幕状态是否满足”，自然属于条件系统。
- 后续 `ImageTarget` 是坐标解析能力，和本 change 的布尔条件不同，应单独设计。

### Decision 2: region 通过脚本窗口解析左上角

如果 `ImageExists.region` 不为空，条件评估模块先用脚本窗口解析 `Rect(left, top, width, height)` 的左上角，再把解析后的屏幕区域传给 `ScreenImageLocator`。宽高保持不变。

如果 `region` 为空，则传 `None` 给 locator，表示由 adapter 在当前屏幕范围内查找。

理由：

- 和 `ColorIs(point)` 一样，脚本内坐标仍然遵守脚本窗口规则。
- 不需要扩展 `Window` 协议暴露窗口矩形，避免为了单个条件污染窗口模型。
- 显式 `region` 鼓励用户缩小搜索范围；没有 region 时仍保留简单可用路径。

### Decision 3: runner 注入 `ScreenImageLocator | None`

`ScriptRunner` 增加可选 `image_locator` 依赖，并在评估条件时传给 `condition_evaluator`。如果脚本执行到 `ImageExists` 但没有注入 locator，评估模块抛出清晰运行错误。

理由：

- 和现有 `color_reader` 模式一致，保持构造注入和可测试性。
- runner 不直接知道 pyautogui、模板文件读取或 macOS 权限。

### Decision 4: dry-run 用显式模板列表表示“图片存在”

CLI/application 新增 dry-run 图片匹配配置，建议命名为 `--dry-run-image <template-path>`，可重复传入。dry-run locator 对这些模板返回固定 `ImageMatch`，其他模板返回 `None`。

理由：

- 能验证 `WaitUntil(ImageExists(...))` 的成功和超时路径。
- 不需要在 CLI 中暴露矩形或置信度复杂配置；第一版只服务可重复验证。
- 后续如果需要测试定位点击，可以再扩展 dry-run image match 的矩形配置。

### Decision 5: 真实运行按需求分析懒加载 image locator

`script_requirements` 增加 `needs_image_locator`。只有脚本步骤树中存在 `ImageExists` 条件时，应用层才创建真实 `ScreenImageLocator`。

理由：

- 保持普通脚本不触发截图权限、模板匹配依赖或 pyautogui 定位能力。
- 和已有 `needs_color_reader` 注入模式一致。

## Risks / Trade-offs

- [Risk] dry-run 只能表达图片是否存在，不能表达真实匹配位置。→ Mitigation: 本 change 只做布尔条件；定位点击会在后续 `ImageTarget` change 中补更完整的 dry-run match 配置。
- [Risk] 用户在 `ImageExists` 中传入任意路径，真实运行会读取该路径。→ Mitigation: 当前脚本仍是 Python 代码定义，不是外部不可信输入；后续脚本文件化或 UI 暴露前再加资产目录/白名单。
- [Risk] 全屏模板匹配可能较慢。→ Mitigation: 条件模型支持 `region`，README 和 demo 鼓励限制区域。
- [Risk] `WaitUntil(ImageExists(...))` 每次轮询都可能截图，真实运行成本高。→ Mitigation: 复用现有 interval/timeout 控制，用户通过较大 interval 和 region 控制成本。
