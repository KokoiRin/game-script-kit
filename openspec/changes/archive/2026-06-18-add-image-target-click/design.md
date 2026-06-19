## Context

当前系统已经具备两层图片能力：`ScreenImageLocator` 可以查找模板图片并返回 `ImageMatch.center`，`ImageExists(...)` 可以把图片存在性接入 `If` 和 `WaitUntil`。但动作仍然只能点击静态 `Point`，无法表达“点击这个图片所在位置”。

这个 change 的目标是把图片匹配结果转成点击坐标，并保持输入设备端口不变。runner 负责把动态目标解析为最终屏幕 `Point`，然后继续调用 `InputDevice.click(point)`。

## Goals / Non-Goals

**Goals:**

- 新增 `ImageTarget(template, region=None, min_confidence=1.0, offset=Point(0, 0))` 领域模型。
- 让 `Click` 支持 `Point | ImageTarget`，保持已有 `Click(Point(...))` 兼容。
- runner 执行 `Click(ImageTarget(...))` 时通过 `ScreenImageLocator` 查找图片，点击匹配中心点加 offset。
- 脚本需求分析能识别图片目标点击需要 image locator。
- dry-run 支持通过 `--dry-run-image` 复现图片目标点击。
- 新增 `click-image-demo`，提供用户可直接运行的 dry-run 验证命令。

**Non-Goals:**

- 不扩展 `Drag` 到图片目标。
- 不实现等待后点击的组合语法；用户仍然可以显式写 `WaitUntil(ImageExists(...))` 后接 `Click(ImageTarget(...))`。
- 不实现多匹配选择、排序、边界夹取、百分比偏移、OCR 或真实浏览器 smoke。
- 不改变 `InputDevice`、`PixelColorReader` 或 `ScreenImageLocator` 端口。

## Decisions

### Decision 1: 使用 `ImageTarget` 表达动态点击目标

建议模型：

```python
@dataclass(frozen=True, slots=True)
class ImageTarget:
    template: ImageTemplate
    region: Rect | None = None
    min_confidence: float = 1.0
    offset: Point = Point(0, 0)
```

`Click` 的字段继续命名为 `point` 以保持现有调用 `Click(Point(...))` 不变，但类型扩展为 `Point | ImageTarget`。后续如果需要更清晰命名，可以在单独兼容 change 中迁移到 `target`。

理由：

- 直接支持用户当前目标：根据图片定位坐标并点击。
- 不提前引入通用 target hierarchy，避免只有一个动态目标时抽象过度。
- 保留 `Click(Point(...))` 的外观和测试期望。

### Decision 2: 图片目标解析得到最终屏幕坐标

runner 解析规则：

1. 如果 click 目标是 `Point`，继续按脚本窗口解析该点。
2. 如果 click 目标是 `ImageTarget`：
   - 如果 target 带 `region`，先按脚本窗口解析 region 左上角，宽高不变。
   - 调用 `ScreenImageLocator.locate(template, region=resolved_region, min_confidence=min_confidence)`。
   - 如果返回 `None`，抛出清晰运行错误。
   - 如果返回 `ImageMatch`，最终点击点是 `match.center + offset`。

理由：

- `ImageMatch.center` 已经是屏幕坐标，不应该再经过脚本窗口二次解析。
- region 仍然遵守脚本窗口坐标，和 `ImageExists.region` 一致。
- offset 是对匹配中心点的微调，用于点击图标旁边或按钮内部特定位置。

### Decision 3: 复用现有 image locator 注入路径

`script_requirements.needs_image_locator` 需要检查 `Click(ImageTarget(...))`。应用层和 CLI 已经能在 dry-run 和真实运行中注入 image locator，本 change 只扩展需求分析和 demo。

理由：

- 不新增端口，不改变平台 adapter。
- dry-run 里 `--dry-run-image` 已经能让指定模板返回固定 `ImageMatch`，足以验证点击路径。

## Risks / Trade-offs

- [Risk] `Click` 字段名仍叫 `point`，但可能保存 `ImageTarget`。→ Mitigation: 这是为了兼容现有脚本；文档明确“点击目标”语义，后续可单独做命名迁移。
- [Risk] dry-run 默认匹配矩形很小，点击坐标可能是 `(0, 0)`。→ Mitigation: 第一版只验证链路；后续图片定位点击增强可以加 `--dry-run-image-match path:x,y,w,h`。
- [Risk] 图片目标未找到会在动作执行时失败。→ Mitigation: 应用层已经归一化运行时 `RuntimeError`；用户可先写 `WaitUntil(ImageExists(...))` 降低失败概率。
- [Risk] offset 使用屏幕像素，可能受缩放影响。→ Mitigation: 和当前 `Point` 坐标模型一致，暂不引入比例/百分比语义。
