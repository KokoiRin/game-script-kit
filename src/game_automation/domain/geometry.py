"""定义脚本领域中用于表达位置和区域的基础几何对象。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Rect:
    left: int
    top: int
    width: int
    height: int

    def __post_init__(self) -> None:
        """校验区域必须有正向宽度和高度。"""
        if self.width <= 0:
            raise ValueError("rect width must be greater than 0")
        if self.height <= 0:
            raise ValueError("rect height must be greater than 0")
