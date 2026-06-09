"""定义平台无关的 RGB 颜色值对象。"""

from __future__ import annotations

from dataclasses import dataclass
import re

_HEX_RGB_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True, slots=True)
class Color:
    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        """校验 RGB 通道必须落在 0 到 255 之间。"""
        for channel_name, value in (
            ("red", self.red),
            ("green", self.green),
            ("blue", self.blue),
        ):
            if not 0 <= value <= 255:
                raise ValueError(f"{channel_name} must be between 0 and 255")

    @classmethod
    def from_hex(cls, value: str) -> "Color":
        """从 #RRGGBB 格式的 RGB 十六进制字符串创建颜色。"""
        if _HEX_RGB_PATTERN.fullmatch(value) is None:
            raise ValueError("color must match #[0-9A-Fa-f]{6}")
        return cls(
            red=int(value[1:3], 16),
            green=int(value[3:5], 16),
            blue=int(value[5:7], 16),
        )

    def __str__(self) -> str:
        """返回 #RRGGBB 格式的 RGB 十六进制展示文本。"""
        return f"#{self.red:02X}{self.green:02X}{self.blue:02X}"
