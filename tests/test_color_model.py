"""验证 RGB 颜色领域模型。"""

from __future__ import annotations

import pytest

from game_automation.domain import Color


def test_color_keeps_rgb_channels() -> None:
    """验证颜色会保留红绿蓝三个通道。"""
    color = Color(red=1, green=2, blue=3)

    assert color.red == 1
    assert color.green == 2
    assert color.blue == 3


def test_color_formats_as_hash_prefixed_rgb_hex() -> None:
    """验证颜色对外展示为 # 开头的 RGB 十六进制。"""
    assert str(Color(red=1, green=10, blue=255)) == "#010AFF"


def test_color_accepts_hash_prefixed_rgb_hex() -> None:
    """验证颜色可以从 # 开头的 RGB 十六进制参数创建。"""
    assert Color.from_hex("#0a14ff") == Color(red=10, green=20, blue=255)


@pytest.mark.parametrize("value", ["0A14FF", "#0A1", "#0A14FG", "#0A14FF00"])
def test_color_rejects_invalid_rgb_hex(value: str) -> None:
    """验证非法 RGB 十六进制参数会被拒绝。"""
    with pytest.raises(ValueError, match="color must match"):
        Color.from_hex(value)


@pytest.mark.parametrize(
    ("red", "green", "blue"),
    [
        (-1, 0, 0),
        (0, -1, 0),
        (0, 0, -1),
        (256, 0, 0),
        (0, 256, 0),
        (0, 0, 256),
    ],
)
def test_color_rejects_channels_outside_byte_range(red: int, green: int, blue: int) -> None:
    """验证颜色通道必须在 0 到 255 之间。"""
    with pytest.raises(ValueError, match="between 0 and 255"):
        Color(red=red, green=green, blue=blue)
