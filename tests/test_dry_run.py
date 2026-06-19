"""验证 dry-run input adapter 的可观测输出。"""

from __future__ import annotations

from game_automation.portable.adapters.dry_run import (
    DryRunInputDevice,
    DryRunPixelColorReader,
    DryRunScreenImageLocator,
)
from game_automation.portable.domain import Color, ImageMatch, ImageTemplate, Point, Rect


def test_dry_run_input_device_prints_click(capsys) -> None:
    """验证 dry-run 点击只打印目标坐标。"""
    DryRunInputDevice().click(Point(1, 2))

    assert capsys.readouterr().out == "click Point(x=1, y=2)\n"


def test_dry_run_input_device_prints_drag(capsys) -> None:
    """验证 dry-run 拖拽只打印起终点和持续时间。"""
    DryRunInputDevice().drag_to(Point(1, 2), Point(3, 4), duration_seconds=0.5)

    assert capsys.readouterr().out == "drag Point(x=1, y=2) -> Point(x=3, y=4) (duration=0.5s)\n"


def test_dry_run_input_device_prints_wait(capsys) -> None:
    """验证 dry-run 等待只打印持续时间。"""
    DryRunInputDevice().wait(0.25)

    assert capsys.readouterr().out == "wait 0.25s\n"


def test_dry_run_pixel_color_reader_returns_fixed_color() -> None:
    """验证 dry-run 取色 reader 始终返回固定颜色。"""
    reader = DryRunPixelColorReader(Color(1, 2, 3))

    assert reader.read_color(Point(10, 20)) == Color(1, 2, 3)


def test_dry_run_screen_image_locator_returns_configured_match() -> None:
    """验证 dry-run 图像定位会返回预设匹配结果。"""
    template = ImageTemplate("assets/start.png")
    match = ImageMatch(Rect(left=10, top=20, width=30, height=40), confidence=0.9)
    locator = DryRunScreenImageLocator({template: match})

    assert locator.locate(template, min_confidence=0.8) == match


def test_dry_run_screen_image_locator_returns_none_for_missing_template() -> None:
    """验证 dry-run 图像定位对未配置模板返回未找到。"""
    locator = DryRunScreenImageLocator({})

    assert locator.locate(ImageTemplate("assets/missing.png")) is None


def test_dry_run_screen_image_locator_respects_min_confidence() -> None:
    """验证 dry-run 图像定位会按最低置信度过滤预设匹配。"""
    template = ImageTemplate("assets/start.png")
    match = ImageMatch(Rect(left=0, top=0, width=10, height=10), confidence=0.7)
    locator = DryRunScreenImageLocator({template: match})

    assert locator.locate(template, min_confidence=0.8) is None
