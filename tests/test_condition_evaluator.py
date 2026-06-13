"""验证脚本条件评估器的运行时行为。"""

import pytest

from game_automation.portable.domain import AreaWindow, Color, ColorIs, Point, Rect
from game_automation.portable.engine.condition_evaluator import evaluate_condition


class FakeColorReader:
    """提供条件评估测试用固定取色结果。"""

    def __init__(self, color: Color) -> None:
        """保存固定颜色并记录读取点。"""
        self.color = color
        self.points: list[Point] = []

    def read_color(self, point: Point) -> Color:
        """记录读取点并返回固定颜色。"""
        self.points.append(point)
        return self.color


def test_condition_evaluator_matches_color_with_tolerance_and_window() -> None:
    """验证颜色条件评估会解析窗口并按每通道容差判断。"""
    reader = FakeColorReader(Color(12, 19, 31))
    condition = ColorIs(Point(5, 6), Color(10, 20, 30), tolerance=2)

    result = evaluate_condition(
        condition,
        window=AreaWindow(Rect(100, 200, 800, 600)),
        color_reader=reader,
    )

    assert result is True
    assert reader.points == [Point(105, 206)]


def test_condition_evaluator_returns_false_for_color_outside_tolerance() -> None:
    """验证任一颜色通道超出容差时条件为假。"""
    reader = FakeColorReader(Color(13, 20, 30))
    condition = ColorIs(Point(5, 6), Color(10, 20, 30), tolerance=2)

    result = evaluate_condition(
        condition,
        window=AreaWindow(Rect(100, 200, 800, 600)),
        color_reader=reader,
    )

    assert result is False


def test_condition_evaluator_requires_color_reader() -> None:
    """验证颜色条件缺少取色端口时由评估器报告错误。"""
    condition = ColorIs(Point(5, 6), Color(10, 20, 30))

    with pytest.raises(RuntimeError, match="color reader"):
        evaluate_condition(
            condition,
            window=AreaWindow(Rect(100, 200, 800, 600)),
            color_reader=None,
        )
