"""实现 engine.ports.ScreenImageLocator，通过 pyautogui 定位屏幕模板图像。

本 module 只封装桌面截图、模板查找和后端错误转换；它不定义脚本条件语义，
也不决定图像匹配能力何时被装配到 runner。
"""

from __future__ import annotations

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
        kwargs = _build_locate_kwargs(region=region, min_confidence=min_confidence)
        try:
            box = self._backend.locateOnScreen(template.path, **kwargs)
        except Exception as exc:
            if self._is_image_not_found(exc):
                return None
            if "confidence" in kwargs and isinstance(exc, TypeError):
                raise RuntimeError(
                    "screen image matching confidence requires backend support. "
                    "Install image matching dependencies such as OpenCV."
                ) from exc
            raise RuntimeError(
                "failed to perform screen image matching. Check template path, "
                "screenshot permissions, and image matching dependencies."
            ) from exc

        if box is None:
            return None
        return ImageMatch(rect=_box_to_rect(box), confidence=min_confidence)

    def _is_image_not_found(self, exc: Exception) -> bool:
        """判断后端异常是否表示未找到模板而不是 setup 失败。"""
        exception_type = getattr(self._backend, "ImageNotFoundException", None)
        return exception_type is not None and isinstance(exc, exception_type)

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


def _validate_min_confidence(min_confidence: float) -> None:
    """校验最低匹配置信度必须大于 0 且不超过 1。"""
    if not 0 < min_confidence <= 1:
        raise ValueError("minimum image match confidence must be greater than 0 and at most 1")


def _build_locate_kwargs(
    *,
    region: Rect | None,
    min_confidence: float,
) -> dict[str, tuple[int, int, int, int] | float]:
    """构造 pyautogui.locateOnScreen 的平台参数。"""
    kwargs: dict[str, tuple[int, int, int, int] | float] = {}
    if region is not None:
        kwargs["region"] = (region.left, region.top, region.width, region.height)
    if min_confidence < 1.0:
        kwargs["confidence"] = min_confidence
    return kwargs


def _box_to_rect(box: object) -> Rect:
    """把 pyautogui Box 或 tuple 结果转换为领域 Rect。"""
    try:
        left = getattr(box, "left")
        top = getattr(box, "top")
        width = getattr(box, "width")
        height = getattr(box, "height")
    except AttributeError:
        left, top, width, height = box  # type: ignore[misc]
    return Rect(left=int(left), top=int(top), width=int(width), height=int(height))
