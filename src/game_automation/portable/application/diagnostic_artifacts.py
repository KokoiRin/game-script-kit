"""生成屏幕诊断图片和裁剪产物。

本 module 负责 Pillow 图像处理、诊断框绘制、裁剪导出、黑屏检测和文件名清理；
它不读取状态配置、不创建截图 adapter，也不处理 HTTP、CLI 或本地控制 facade。
ScreenDiagnosticsUseCase 负责决定何时调用这些 artifact helper。
"""

from __future__ import annotations

from pathlib import Path

from game_automation.portable.domain import NamedRegion, Point, Rect, ScreenStateProbeResult

BLANK_SCREENSHOT_WARNING = (
    "warning: captured screenshot appears all black. "
    "Check macOS Screen Recording permission, foreground window, or desktop session.\n"
)


def draw_region_diagnostics(
    *,
    screenshot_path: Path,
    output_path: Path,
    screen_size: Point,
    regions: tuple[NamedRegion, ...],
) -> None:
    """把命名区域绘制到截图上并保存诊断图。"""
    _ensure_positive_screen_size(screen_size)

    from PIL import Image, ImageDraw, ImageFont

    with Image.open(screenshot_path) as image:
        diagnostic = image.convert("RGB")
    draw = ImageDraw.Draw(diagnostic)
    font = _load_region_label_font(ImageFont)
    scale_x = diagnostic.width / screen_size.x
    scale_y = diagnostic.height / screen_size.y
    for index, region in enumerate(regions, start=1):
        color = _region_color(index)
        box = _region_box_in_pixels(region.region, scale_x=scale_x, scale_y=scale_y)
        draw.rectangle(box, outline=color, width=3)
        _draw_region_label(draw, font, f"{index}. {region.name}", box, color)
    diagnostic.save(output_path)


def draw_probe_diagnostics(
    *,
    screenshot_path: Path,
    output_path: Path,
    screen_size: Point,
    regions: tuple[NamedRegion, ...],
    result: ScreenStateProbeResult,
) -> None:
    """把命名区域和状态候选最佳位置绘制到截图上并保存。"""
    _ensure_positive_screen_size(screen_size)

    from PIL import Image, ImageDraw, ImageFont

    with Image.open(screenshot_path) as image:
        diagnostic = image.convert("RGB")
    draw = ImageDraw.Draw(diagnostic)
    font = _load_region_label_font(ImageFont)
    scale_x = diagnostic.width / screen_size.x
    scale_y = diagnostic.height / screen_size.y
    for index, region in enumerate(regions, start=1):
        color = _region_color(index)
        box = _region_box_in_pixels(region.region, scale_x=scale_x, scale_y=scale_y)
        draw.rectangle(box, outline=color, width=2)
        _draw_region_label(draw, font, f"R{index}. {region.name}", box, color)
    for index, candidate in enumerate(result.candidates, start=1):
        if candidate.best_rect is None:
            continue
        color = _probe_candidate_color(candidate)
        box = _region_box_in_pixels(candidate.best_rect, scale_x=scale_x, scale_y=scale_y)
        draw.rectangle(box, outline=color, width=3)
        _draw_region_label(draw, font, _probe_candidate_label(index, candidate), box, color)
    diagnostic.save(output_path)


def save_region_crops(
    *,
    screenshot_path: Path,
    output_folder: Path,
    screen_size: Point,
    regions: tuple[NamedRegion, ...],
) -> tuple[Path, ...]:
    """按命名区域把截图裁剪成独立图片并返回保存路径。"""
    _ensure_positive_screen_size(screen_size)

    from PIL import Image

    saved_paths = []
    with Image.open(screenshot_path) as image:
        scale_x = image.width / screen_size.x
        scale_y = image.height / screen_size.y
        for region in regions:
            box = _region_box_in_pixels(region.region, scale_x=scale_x, scale_y=scale_y)
            output_path = output_folder / f"{safe_region_crop_name(region.name)}.png"
            image.crop(box).save(output_path)
            saved_paths.append(output_path)
    return tuple(saved_paths)


def save_probe_candidate_crops(
    *,
    screenshot_path: Path,
    output_folder: Path,
    screen_size: Point,
    result: ScreenStateProbeResult,
) -> tuple[Path, ...]:
    """按候选最佳位置把截图裁剪成独立图片并返回保存路径。"""
    _ensure_positive_screen_size(screen_size)

    from PIL import Image

    saved_paths = []
    with Image.open(screenshot_path) as image:
        scale_x = image.width / screen_size.x
        scale_y = image.height / screen_size.y
        for index, candidate in enumerate(result.candidates, start=1):
            if candidate.best_rect is None:
                continue
            box = _region_box_in_pixels(candidate.best_rect, scale_x=scale_x, scale_y=scale_y)
            output_path = output_folder / f"{_safe_probe_crop_name(index, candidate)}.png"
            image.crop(box).save(output_path)
            saved_paths.append(output_path)
    return tuple(saved_paths)


def screen_capture_health_warning(path: Path) -> str:
    """检查已保存截图是否疑似全黑，并返回用户可见警告。"""
    try:
        from PIL import Image

        with Image.open(path) as image:
            extrema = image.convert("RGB").getextrema()
    except Exception:
        return ""
    return BLANK_SCREENSHOT_WARNING if _rgb_extrema_are_near_black(extrema) else ""


def refresh_crop_output_folder(output_folder: Path) -> None:
    """删除裁剪输出目录中的旧 PNG，让目录只代表本轮导出结果。"""
    for path in output_folder.glob("*.png"):
        if path.is_file():
            path.unlink()


def safe_region_crop_name(name: str) -> str:
    """把区域名转换成不含路径分隔符的裁剪文件名。"""
    return "".join("_" if char in {"/", "\\", ":"} else char for char in name).strip() or "region"


def _ensure_positive_screen_size(screen_size: Point) -> None:
    """拒绝无法换算截图像素比例的屏幕尺寸。"""
    if screen_size.x <= 0 or screen_size.y <= 0:
        raise ValueError("screen size must be positive")


def _safe_probe_crop_name(index: int, candidate) -> str:
    """生成不含路径分隔符的探测候选裁剪文件名。"""
    parts = [f"{index:02d}", candidate.candidate.name]
    if candidate.candidate.search_name:
        parts.append(candidate.candidate.search_name)
    return safe_region_crop_name("_".join(parts))


def _rgb_extrema_are_near_black(
    extrema: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
) -> bool:
    """判断 RGB 极值是否表示整张截图接近纯黑。"""
    return all(channel_max <= 2 for _, channel_max in extrema)


def _region_box_in_pixels(region: Rect, *, scale_x: float, scale_y: float) -> tuple[int, int, int, int]:
    """把点坐标矩形换算成截图像素矩形。"""
    return (
        round(region.left * scale_x),
        round(region.top * scale_y),
        round((region.left + region.width) * scale_x),
        round((region.top + region.height) * scale_y),
    )


def _draw_region_label(draw, font, label: str, box: tuple[int, int, int, int], color: str) -> None:
    """在区域框左上角绘制区域名称，字体不支持时使用编号兜底。"""
    left, top, _, _ = box
    text = label
    try:
        text_box = draw.textbbox((left, top), text, font=font)
    except UnicodeEncodeError:
        text = label.split(".", 1)[0]
        text_box = draw.textbbox((left, top), text, font=font)
    background = (
        text_box[0] - 2,
        text_box[1] - 2,
        text_box[2] + 2,
        text_box[3] + 2,
    )
    draw.rectangle(background, fill=color)
    draw.text((left, top), text, fill="#ffffff", font=font)


def _load_region_label_font(image_font_module):
    """加载适合中文区域名的字体，找不到时回退到 Pillow 默认字体。"""
    candidates = (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "DejaVuSans.ttf",
    )
    for candidate in candidates:
        try:
            return image_font_module.truetype(candidate, 14)
        except OSError:
            continue
    return image_font_module.load_default()


def _region_color(index: int) -> str:
    """按区域序号返回稳定的高对比描边颜色。"""
    colors = ("#ef4444", "#22c55e", "#3b82f6", "#f59e0b", "#a855f7", "#14b8a6")
    return colors[(index - 1) % len(colors)]


def _probe_candidate_label(index: int, candidate) -> str:
    """生成探测诊断候选框标签。"""
    name = candidate.candidate.name
    if candidate.candidate.search_name:
        name = f"{name}/{candidate.candidate.search_name}"
    confidence = "无" if candidate.best_confidence is None else f"{candidate.best_confidence:.3f}"
    return f"C{index}. {name} {_probe_candidate_status_label(candidate)} {confidence}"


def _probe_candidate_status_label(candidate) -> str:
    """返回探测诊断候选状态标签。"""
    if candidate.skipped:
        return "跳过"
    if candidate.found:
        return "命中"
    return "未命中"


def _probe_candidate_color(candidate) -> str:
    """按候选探测状态返回诊断框颜色。"""
    if candidate.skipped:
        return "#6b7280"
    if candidate.found:
        return "#16a34a"
    return "#dc2626"
