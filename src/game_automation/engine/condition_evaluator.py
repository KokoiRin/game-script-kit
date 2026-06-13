"""评估脚本运行时条件。

本 module 只把条件模型、脚本窗口和已注入端口组合成布尔结果；它不推进时间、
不触发输入动作，也不创建取色 adapter。
"""

from __future__ import annotations

from game_automation.domain import Color, ColorIs
from game_automation.domain.conditions import Condition
from game_automation.domain.windows import Window
from game_automation.engine.ports import PixelColorReader


def evaluate_condition(
    condition: Condition,
    *,
    window: Window,
    color_reader: PixelColorReader | None,
) -> bool:
    """根据运行时端口和脚本窗口评估条件。"""
    if isinstance(condition, ColorIs):
        return _evaluate_color_is(condition, window=window, color_reader=color_reader)
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
