"""定义脚本领域中用于表达位置和区域的基础几何对象。

本 module 只保存坐标和矩形值对象及其不变量；它不做窗口解析之外的运行时行为。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int

    def offset(self, *, x: int = 0, y: int = 0) -> "Point":
        """返回基于当前点位偏移后的新点位。"""
        return Point(self.x + x, self.y + y)


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
