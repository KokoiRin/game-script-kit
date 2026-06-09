"""验证桌面单点取色 adapter 行为。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from game_automation.adapters.desktop import PyAutoGuiPixelColorReader
from game_automation.domain import Color, Point


class FakeImage:
    def __init__(self, pixel) -> None:
        """初始化会返回固定像素的 fake image。"""
        self.pixel = pixel
        self.requested_points = []

    def getpixel(self, point_tuple):
        """记录读取坐标并返回固定像素。"""
        self.requested_points.append(point_tuple)
        return self.pixel


class FailingImage:
    def getpixel(self, point_tuple):
        """读取像素时抛出固定错误。"""
        raise RuntimeError("blocked")


def test_pixel_color_reader_returns_color_from_rgb_pixel() -> None:
    """验证 RGB 像素会转换为 Color。"""
    image = FakeImage((10, 20, 30))
    backend = SimpleNamespace(screenshot=lambda: image)

    color = PyAutoGuiPixelColorReader(backend=backend).read_color(Point(7, 8))

    assert color == Color(10, 20, 30)
    assert image.requested_points == [(7, 8)]


def test_pixel_color_reader_ignores_alpha_channel() -> None:
    """验证 RGBA 像素只取前三个 RGB 通道。"""
    image = FakeImage((11, 22, 33, 44))
    backend = SimpleNamespace(screenshot=lambda: image)

    assert PyAutoGuiPixelColorReader(backend=backend).read_color(Point(1, 2)) == Color(11, 22, 33)


def test_pixel_color_reader_wraps_screenshot_errors() -> None:
    """验证截图失败会被包装成清晰 setup 错误。"""
    backend = SimpleNamespace(
        screenshot=lambda: (_ for _ in ()).throw(RuntimeError("blocked"))
    )

    with pytest.raises(RuntimeError, match="screen color"):
        PyAutoGuiPixelColorReader(backend=backend).read_color(Point(1, 2))


def test_pixel_color_reader_wraps_getpixel_errors() -> None:
    """验证读取像素失败会被包装成清晰 setup 错误。"""
    backend = SimpleNamespace(screenshot=lambda: FailingImage())

    with pytest.raises(RuntimeError, match="screen color"):
        PyAutoGuiPixelColorReader(backend=backend).read_color(Point(1, 2))
