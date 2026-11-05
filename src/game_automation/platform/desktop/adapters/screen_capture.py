"""提供桌面截图及物理像素和逻辑坐标转换。

本 module 同时供识图与素材准备 adapter 使用；不匹配模板、不运行脚本，
也不选择目标窗口。backend 由调用方注入以保持设备访问延迟。
"""

from dataclasses import dataclass

from PIL import Image

from game_automation.portable.domain.geometry import Rect


@dataclass(frozen=True, slots=True)
class CapturedScreen:
    """保留截图像素、逻辑原点和每轴像素比例。"""

    image: Image.Image
    origin_left_pixels: int
    origin_top_pixels: int
    pixels_per_point_x: float
    pixels_per_point_y: float


def capture_screen(backend: object, *, region: Rect | None = None) -> CapturedScreen:
    """截取主屏幕并按可选逻辑坐标区域裁剪。"""
    image = backend.screenshot().convert("RGB")
    size = backend.size()
    try:
        width, height = int(size.width), int(size.height)
    except AttributeError:
        width, height = map(int, size)
    if width <= 0 or height <= 0:
        raise RuntimeError("screen pointer size must be positive")
    screen = CapturedScreen(image, 0, 0, image.width / width, image.height / height)
    return screen if region is None else crop_captured_screen(screen, region=region)


def crop_captured_screen(screen: CapturedScreen, *, region: Rect) -> CapturedScreen:
    """按屏幕逻辑范围裁剪截图，保留匹配结果还原坐标所需的原点。"""
    left = round(region.left * screen.pixels_per_point_x)
    top = round(region.top * screen.pixels_per_point_y)
    right = round((region.left + region.width) * screen.pixels_per_point_x)
    bottom = round((region.top + region.height) * screen.pixels_per_point_y)
    return CapturedScreen(
        screen.image.crop((left - screen.origin_left_pixels, top - screen.origin_top_pixels,
                           right - screen.origin_left_pixels, bottom - screen.origin_top_pixels)),
        left, top, screen.pixels_per_point_x, screen.pixels_per_point_y,
    )
