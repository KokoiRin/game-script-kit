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
    ScreenStateIs,
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


class FakeScreenStateReader:
    """提供条件评估测试用固定界面状态。"""

    def __init__(self, state: str) -> None:
        """保存固定状态并记录读取请求。"""
        self.state = state
        self.calls = []

    def read_current_state(self, *, min_confidence: float = 0.8, logger=None) -> str:
        """记录最低置信度并返回固定状态。"""
        self.calls.append(min_confidence)
        return self.state


class FakeRunLogger:
    """收集条件评估测试中的运行日志。"""

    def __init__(self) -> None:
        """初始化日志列表。"""
        self.messages: list[str] = []

    def log(self, message: str) -> None:
        """记录一条运行日志。"""
        self.messages.append(message)


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


def test_condition_evaluator_returns_true_when_screen_state_matches() -> None:
    """验证界面状态条件会通过状态读取端口返回真。"""
    reader = FakeScreenStateReader("主页")

    result = evaluate_condition(
        ScreenStateIs("主页", min_confidence=0.7),
        window=AreaWindow(Rect(100, 200, 800, 600)),
        color_reader=None,
        image_locator=None,
        screen_state_reader=reader,
    )

    assert result is True
    assert reader.calls == [0.7]


def test_condition_evaluator_logs_screen_state_match() -> None:
    """验证界面状态条件评估会记录实际状态和命中结果。"""
    reader = FakeScreenStateReader("主页")
    logger = FakeRunLogger()

    result = evaluate_condition(
        ScreenStateIs("主页", min_confidence=0.7),
        window=AreaWindow(Rect(100, 200, 800, 600)),
        color_reader=None,
        image_locator=None,
        screen_state_reader=reader,
        logger=logger,
    )

    assert result is True
    assert logger.messages == [
        "screen state condition expected=主页 actual=主页 min_confidence=0.7 matched=True"
    ]


def test_condition_evaluator_returns_false_when_screen_state_differs() -> None:
    """验证界面状态不一致时条件为假。"""
    reader = FakeScreenStateReader("人物")

    result = evaluate_condition(
        ScreenStateIs("主页"),
        window=AreaWindow(Rect(100, 200, 800, 600)),
        color_reader=None,
        image_locator=None,
        screen_state_reader=reader,
    )

    assert result is False


def test_condition_evaluator_requires_screen_state_reader() -> None:
    """验证界面状态条件缺少读取端口时由评估器报告错误。"""
    with pytest.raises(RuntimeError, match="screen state reader"):
        evaluate_condition(
            ScreenStateIs("主页"),
            window=AreaWindow(Rect(100, 200, 800, 600)),
            color_reader=None,
            image_locator=None,
        )


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
