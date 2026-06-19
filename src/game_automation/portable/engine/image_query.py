"""通过图像定位端口执行平台无关的图片匹配查询。

本 module 负责把图片引用解析为 ImageTemplate，并调用已注入的
ScreenImageLocator；它不创建真实 adapter、不截图，也不解释点击或条件语义。
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from game_automation.portable.domain import ImageLookupResult, ImageRef, ImageTemplate, Rect, TargetCatalog
from game_automation.portable.engine.ports import RunLogger, ScreenImageLocator


def locate_image(
    image: ImageTemplate | ImageRef,
    *,
    image_locator: ScreenImageLocator | None,
    resources: TargetCatalog,
    region: Rect | None = None,
    min_confidence: float = 1.0,
    logger: RunLogger | None = None,
    clock: Callable[[], float] = perf_counter,
) -> ImageLookupResult:
    """解析图片引用并返回一次图片匹配查询结果。"""
    if image_locator is None:
        raise RuntimeError("image locator is required for image lookup")
    template = resources.resolve_image(image)
    started_at = clock()
    match = image_locator.locate(
        template,
        region=region,
        min_confidence=min_confidence,
        logger=logger,
    )
    elapsed_ms = (clock() - started_at) * 1000
    _log_image_match(
        logger,
        template=template,
        region=region,
        min_confidence=min_confidence,
        elapsed_ms=elapsed_ms,
        result=ImageLookupResult(match),
    )
    return ImageLookupResult(match)


def _log_image_match(
    logger: RunLogger | None,
    *,
    template: ImageTemplate,
    region: Rect | None,
    min_confidence: float,
    elapsed_ms: float,
    result: ImageLookupResult,
) -> None:
    """在调用方需要时记录一次图片匹配诊断。"""
    if logger is None:
        return
    logger.log(
        "image match "
        f"template={template.path} "
        f"min_confidence={min_confidence} "
        f"region={region} "
        f"elapsed_ms={elapsed_ms:.2f} "
        f"found={result.found} "
        f"confidence={result.confidence}"
    )
