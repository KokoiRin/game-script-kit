"""实现 engine.ports.ScreenImageLocator，通过 pyautogui 截图和 OpenCV 定位模板图像。

本 module 只封装桌面截图、模板读取、OpenCV 匹配和后端错误转换；它不定义
脚本条件语义，也不决定图像匹配能力何时被装配到 runner。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from PIL import Image

from game_automation.portable.domain import ImageMatch, ImageTemplate, Rect
from game_automation.portable.engine.ports import ScreenImageLocator


class PyAutoGuiScreenImageLocator(ScreenImageLocator):
    def __init__(self, backend: object | None = None) -> None:
        """初始化屏幕图像定位 adapter，可注入 backend 便于测试。"""
        self._backend = backend if backend is not None else self._load_backend()

    def locate(
        self,
        template: ImageTemplate,
        *,
        region: Rect | None = None,
        min_confidence: float = 1.0,
    ) -> ImageMatch | None:
        """在当前屏幕或指定区域内查找模板图片。"""
        _validate_min_confidence(min_confidence)
        try:
            cv2, numpy = _load_cv_modules()
            screenshot = _capture_screen(self._backend, region=region)
            template_image = _load_template_image(template)
            return _locate_template(
                cv2=cv2,
                numpy=numpy,
                screenshot=screenshot,
                template=template_image,
                min_confidence=min_confidence,
            )
        except Exception as exc:
            if _is_setup_error(exc):
                raise exc
            raise RuntimeError(
                "failed to perform screen image matching. Check template path, "
                "screenshot permissions, and image matching dependencies."
            ) from exc

    def _load_backend(self) -> object:
        """延迟加载 pyautogui，避免导入工具模块时触发平台依赖。"""
        try:
            import pyautogui
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "pyautogui is required for screen image matching. "
                "Install dependencies with: pip install -e \".[dev]\""
            ) from exc
        return pyautogui


@dataclass(frozen=True, slots=True)
class CapturedScreen:
    image: Image.Image
    origin_left_pixels: int
    origin_top_pixels: int
    pixels_per_point_x: float
    pixels_per_point_y: float


def _load_cv_modules() -> tuple[ModuleType, ModuleType]:
    """延迟加载 OpenCV 和 numpy，避免普通导入触发图像匹配依赖。"""
    try:
        import cv2
        import numpy
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV-backed screen image matching requires opencv-python-headless "
            "and numpy. Install dependencies with: pip install -e ."
        ) from exc
    return cv2, numpy


def _capture_screen(backend: object, *, region: Rect | None) -> CapturedScreen:
    """截取屏幕并按鼠标坐标系区域裁剪。"""
    screenshot = backend.screenshot().convert("RGB")
    pixels_per_point_x, pixels_per_point_y = _calculate_pixels_per_point(
        backend,
        screenshot,
    )
    if region is None:
        return CapturedScreen(
            image=screenshot,
            origin_left_pixels=0,
            origin_top_pixels=0,
            pixels_per_point_x=pixels_per_point_x,
            pixels_per_point_y=pixels_per_point_y,
        )

    left = round(region.left * pixels_per_point_x)
    top = round(region.top * pixels_per_point_y)
    right = round((region.left + region.width) * pixels_per_point_x)
    bottom = round((region.top + region.height) * pixels_per_point_y)
    return CapturedScreen(
        image=screenshot.crop((left, top, right, bottom)),
        origin_left_pixels=left,
        origin_top_pixels=top,
        pixels_per_point_x=pixels_per_point_x,
        pixels_per_point_y=pixels_per_point_y,
    )


def _calculate_pixels_per_point(backend: object, screenshot: Image.Image) -> tuple[float, float]:
    """计算截图像素到鼠标坐标点的缩放比例。"""
    pointer_width, pointer_height = _read_pointer_size(backend)
    if pointer_width <= 0 or pointer_height <= 0:
        raise RuntimeError("screen pointer size must be positive")
    return screenshot.width / pointer_width, screenshot.height / pointer_height


def _read_pointer_size(backend: object) -> tuple[int, int]:
    """读取 pyautogui 鼠标坐标系尺寸。"""
    size = backend.size()
    try:
        return int(size.width), int(size.height)
    except AttributeError:
        width, height = size
        return int(width), int(height)


def _load_template_image(template: ImageTemplate) -> Image.Image:
    """读取模板图片并转换为 OpenCV 可匹配的 RGB 图。"""
    with Image.open(Path(template.path)) as image:
        return image.convert("RGB")


def _locate_template(
    *,
    cv2: ModuleType,
    numpy: ModuleType,
    screenshot: CapturedScreen,
    template: Image.Image,
    min_confidence: float,
) -> ImageMatch | None:
    """用 OpenCV 模板匹配返回满足阈值的最佳匹配。"""
    if template.width > screenshot.image.width or template.height > screenshot.image.height:
        return None

    screenshot_array = numpy.array(screenshot.image)
    template_array = numpy.array(template)
    result = cv2.matchTemplate(screenshot_array, template_array, cv2.TM_CCOEFF_NORMED)
    _, max_score, _, max_location = cv2.minMaxLoc(result)
    confidence = float(max_score)
    if confidence < min_confidence:
        return None

    left_pixels = int(max_location[0]) + screenshot.origin_left_pixels
    top_pixels = int(max_location[1]) + screenshot.origin_top_pixels
    return ImageMatch(
        rect=Rect(
            left=round(left_pixels / screenshot.pixels_per_point_x),
            top=round(top_pixels / screenshot.pixels_per_point_y),
            width=round(template.width / screenshot.pixels_per_point_x),
            height=round(template.height / screenshot.pixels_per_point_y),
        ),
        confidence=confidence,
    )


def _is_setup_error(exc: Exception) -> bool:
    """判断异常是否已经是本 adapter 生成的清晰 setup 错误。"""
    return isinstance(exc, RuntimeError) and (
        "OpenCV-backed screen image matching" in str(exc)
        or "screen pointer size" in str(exc)
    )


def _validate_min_confidence(min_confidence: float) -> None:
    """校验最低匹配置信度必须大于 0 且不超过 1。"""
    if not 0 < min_confidence <= 1:
        raise ValueError("minimum image match confidence must be greater than 0 and at most 1")
