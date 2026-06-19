"""通过图像定位端口执行平台无关的图片匹配查询。

本 module 负责把图片引用解析为 ImageTemplate，并调用已注入的
ScreenImageLocator；它不创建真实 adapter、不截图，也不解释点击或条件语义。
"""

from __future__ import annotations

from game_automation.portable.domain import ImageLookupResult, ImageRef, ImageTemplate, Rect, TargetCatalog
from game_automation.portable.engine.ports import ScreenImageLocator


def locate_image(
    image: ImageTemplate | ImageRef,
    *,
    image_locator: ScreenImageLocator | None,
    resources: TargetCatalog,
    region: Rect | None = None,
    min_confidence: float = 1.0,
) -> ImageLookupResult:
    """解析图片引用并返回一次图片匹配查询结果。"""
    if image_locator is None:
        raise RuntimeError("image locator is required for image lookup")
    template = resources.resolve_image(image)
    return ImageLookupResult(
        image_locator.locate(
            template,
            region=region,
            min_confidence=min_confidence,
        )
    )
