"""验证脚本条件评估器的运行时行为。"""

import pytest

from game_automation.portable.domain import (
    AreaWindow,
    Color,
    ColorIs,
    ImageExists,
    ImageRef,
    ImageMatch,
    ImageTemplate,
    NamedImage,
    Point,
    Rect,
    TargetCatalog,
    UnknownImageNameError,
)
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


class FakeImageLocator:
    """提供条件评估测试用固定图像匹配结果。"""

    def __init__(self, match: ImageMatch | None) -> None:
        """保存固定匹配结果并记录定位请求。"""
        self.match = match
        self.calls = []

    def locate(
        self,
        template: ImageTemplate,
        *,
        region: Rect | None = None,
        min_confidence: float = 1.0,
        logger=None,
    ) -> ImageMatch | None:
        """记录定位参数并返回固定匹配结果。"""
        self.calls.append((template, region, min_confidence))
        return self.match


def test_condition_evaluator_matches_color_with_tolerance_and_window() -> None:
    """验证颜色条件评估会解析窗口并按每通道容差判断。"""
    reader = FakeColorReader(Color(12, 19, 31))
    condition = ColorIs(Point(5, 6), Color(10, 20, 30), tolerance=2)

    result = evaluate_condition(
        condition,
        window=AreaWindow(Rect(100, 200, 800, 600)),
        color_reader=reader,
        image_locator=None,
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
        image_locator=None,
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
            image_locator=None,
        )


def test_condition_evaluator_returns_true_when_image_exists() -> None:
    """验证图片存在条件会通过图像定位端口返回真。"""
    locator = FakeImageLocator(ImageMatch(Rect(10, 20, 30, 40), confidence=1.0))
    condition = ImageExists(ImageTemplate("assets/start.png"))

    result = evaluate_condition(
        condition,
        window=AreaWindow(Rect(100, 200, 800, 600)),
        color_reader=None,
        image_locator=locator,
    )

    assert result is True
    assert locator.calls == [(ImageTemplate("assets/start.png"), None, 1.0)]


def test_condition_evaluator_resolves_named_image() -> None:
    """验证图片存在条件会把命名图片解析为模板后再定位。"""
    locator = FakeImageLocator(ImageMatch(Rect(10, 20, 30, 40), confidence=1.0))
    condition = ImageExists(ImageRef("开始按钮"))
    catalog = TargetCatalog(images=(NamedImage("开始按钮", ImageTemplate("assets/start.png")),))

    result = evaluate_condition(
        condition,
        window=AreaWindow(Rect(100, 200, 800, 600)),
        color_reader=None,
        image_locator=locator,
        resources=catalog,
    )

    assert result is True
    assert locator.calls == [(ImageTemplate("assets/start.png"), None, 1.0)]


def test_condition_evaluator_reports_unknown_named_image() -> None:
    """验证未知图片名称会在条件评估时报错。"""
    condition = ImageExists(ImageRef("开始按钮"))

    with pytest.raises(UnknownImageNameError, match="unknown image target: 开始按钮"):
        evaluate_condition(
            condition,
            window=AreaWindow(Rect(100, 200, 800, 600)),
            color_reader=None,
            image_locator=FakeImageLocator(None),
            resources=TargetCatalog(),
        )


def test_condition_evaluator_returns_false_when_image_is_missing() -> None:
    """验证图片不存在条件会通过图像定位端口返回假。"""
    locator = FakeImageLocator(None)
    condition = ImageExists(ImageTemplate("assets/start.png"))

    result = evaluate_condition(
        condition,
        window=AreaWindow(Rect(100, 200, 800, 600)),
        color_reader=None,
        image_locator=locator,
    )

    assert result is False


def test_condition_evaluator_resolves_image_region_with_window() -> None:
    """验证图片条件搜索区域会按脚本窗口解析左上角。"""
    locator = FakeImageLocator(ImageMatch(Rect(110, 220, 30, 40), confidence=0.8))
    condition = ImageExists(
        ImageTemplate("assets/start.png"),
        region=Rect(10, 20, 30, 40),
        min_confidence=0.8,
    )

    evaluate_condition(
        condition,
        window=AreaWindow(Rect(100, 200, 800, 600)),
        color_reader=None,
        image_locator=locator,
    )

    assert locator.calls == [
        (
            ImageTemplate("assets/start.png"),
            Rect(110, 220, 30, 40),
            0.8,
        )
    ]


def test_condition_evaluator_requires_image_locator() -> None:
    """验证图片条件缺少图像定位端口时由评估器报告错误。"""
    condition = ImageExists(ImageTemplate("assets/start.png"))

    with pytest.raises(RuntimeError, match="image locator"):
        evaluate_condition(
            condition,
            window=AreaWindow(Rect(100, 200, 800, 600)),
            color_reader=None,
            image_locator=None,
        )
