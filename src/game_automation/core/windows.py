"""定义脚本执行窗口，以及窗口内坐标到屏幕坐标的解析规则。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from game_automation.core.geometry import Point, Rect


class Window(Protocol):
    def resolve(self, point: Point) -> Point:
        """把窗口内点解析为屏幕坐标点。"""


@dataclass(frozen=True, slots=True)
class ScreenWindow:
    def resolve(self, point: Point) -> Point:
        """屏幕窗口直接使用传入点作为屏幕坐标。"""
        return point


@dataclass(frozen=True, slots=True)
class AreaWindow:
    rect: Rect

    def resolve(self, point: Point) -> Point:
        """把区域内点按区域左上角偏移解析为屏幕坐标。"""
        # 第一版不做边界夹取；区域外点也按同一偏移规则解析，便于脚本调试。
        return Point(self.rect.left + point.x, self.rect.top + point.y)
