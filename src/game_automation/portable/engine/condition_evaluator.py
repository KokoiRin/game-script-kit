"""评估脚本运行时条件。

本 module 只把条件模型、脚本窗口和已注入端口组合成布尔结果；它不推进时间、
不触发输入动作，也不创建取色 adapter。
"""

from __future__ import annotations

from game_automation.portable.domain import Color, ColorIs, ImageExists, Point, Rect, ScreenStateIs
from game_automation.portable.domain.conditions import Condition
from game_automation.portable.domain.point_aliases import TargetCatalog
from game_automation.portable.domain.windows import Window
from game_automation.portable.engine.image_query import locate_image
from game_automation.portable.engine.ports import PixelColorReader, RunLogger, ScreenImageLocator, ScreenStateReader


def evaluate_condition(
    condition: Condition,
    *,
    window: Window,
    color_reader: PixelColorReader | None,
    image_locator: ScreenImageLocator | None,
    screen_state_reader: ScreenStateReader | None = None,
    resources: TargetCatalog | None = None,
    logger: RunLogger | None = None,
) -> bool:
    """根据运行时端口和脚本窗口评估条件。"""
    target_catalog = resources if resources is not None else TargetCatalog()
    if isinstance(condition, ColorIs):
        return _evaluate_color_is(condition, window=window, color_reader=color_reader)
    if isinstance(condition, ImageExists):
        return _evaluate_image_exists(
            condition,
            window=window,
            image_locator=image_locator,
            resources=target_catalog,
            logger=logger,
        )
    if isinstance(condition, ScreenStateIs):
        return _evaluate_screen_state_is(
            condition,
            screen_state_reader=screen_state_reader,
            logger=logger,
        )
    raise TypeError(f"unsupported script condition: {type(condition).__name__}")


def _evaluate_color_is(
    condition: ColorIs,
    *,
    window: Window,
    color_reader: PixelColorReader | None,
) -> bool:
    """读取条件点颜色并按每通道容差判断是否匹配。"""
    if color_reader is None:
        raise RuntimeError("color reader is required for color conditions")

    actual = color_reader.read_color(window.resolve(condition.point))
    return _color_matches(actual, condition.expected, condition.tolerance)


def _color_matches(actual: Color, expected: Color, tolerance: int) -> bool:
    """判断实际颜色是否落在期望颜色的每通道容差内。"""
    return (
        abs(actual.red - expected.red) <= tolerance
        and abs(actual.green - expected.green) <= tolerance
        and abs(actual.blue - expected.blue) <= tolerance
    )


def _evaluate_image_exists(
    condition: ImageExists,
    *,
    window: Window,
    image_locator: ScreenImageLocator | None,
    resources: TargetCatalog,
    logger: RunLogger | None,
) -> bool:
    """通过图像定位端口判断模板图片是否存在。"""
    if image_locator is None:
        raise RuntimeError("image locator is required for image conditions")

    result = locate_image(
        condition.template,
        image_locator=image_locator,
        resources=resources,
        region=_resolve_region(window, condition.region),
        min_confidence=condition.min_confidence,
        logger=logger,
    )
    return result.found


def _evaluate_screen_state_is(
    condition: ScreenStateIs,
    *,
    screen_state_reader: ScreenStateReader | None,
    logger: RunLogger | None,
) -> bool:
    """通过界面状态读取端口判断当前状态是否匹配。"""
    if screen_state_reader is None:
        raise RuntimeError("screen state reader is required for screen state conditions")

    actual_state = screen_state_reader.read_current_state(
        min_confidence=condition.min_confidence,
        logger=logger,
    )
    matched = actual_state == condition.state
    if logger is not None:
        logger.log(
            "screen state condition "
            f"expected={condition.state} "
            f"actual={actual_state} "
            f"min_confidence={condition.min_confidence} "
            f"matched={matched}"
        )
    return matched


def _resolve_region(window: Window, region: Rect | None) -> Rect | None:
    """按脚本窗口解析图片搜索区域的左上角。"""
    if region is None:
        return None
    top_left = window.resolve(_region_top_left(region))
    return Rect(
        left=top_left.x,
        top=top_left.y,
        width=region.width,
        height=region.height,
    )


def _region_top_left(region: Rect) -> Point:
    """把 Rect 左上角转换为窗口可解析的点。"""
    return Point(region.left, region.top)
