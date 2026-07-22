"""定义脚本执行窗口，以及窗口内坐标到屏幕坐标的解析规则。

本 module 只负责窗口坐标解析的领域规则；它不读写真实窗口状态，
也不负责寻找或激活应用窗口。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from game_automation.portable.domain.geometry import Point, Rect


class Window(Protocol):
    def resolve(self, point: Point) -> Point:
        """把窗口内点解析为屏幕坐标点。"""

    def resolve_region(self, region: Rect | None) -> Rect | None:
        """把可选窗口内区域解析为屏幕图片搜索区域。"""


@dataclass(frozen=True, slots=True)
class ScreenWindow:
    def resolve(self, point: Point) -> Point:
        """屏幕窗口直接使用传入点作为屏幕坐标。"""
        return point

    def resolve_region(self, region: Rect | None) -> Rect | None:
        """屏幕窗口保持整屏默认或显式屏幕搜索区域。"""
        return region


@dataclass(frozen=True, slots=True)
class AreaWindow:
    rect: Rect

    def resolve(self, point: Point) -> Point:
        """把区域内点按区域左上角偏移解析为屏幕坐标。"""
        # 第一版不做边界夹取；区域外点也按同一偏移规则解析，便于脚本调试。
        return Point(self.rect.left + point.x, self.rect.top + point.y)

    def resolve_region(self, region: Rect | None) -> Rect:
        """把默认或显式窗口内区域解析为屏幕搜索区域。"""
        if region is None:
            return self.rect
        top_left = self.resolve(Point(region.left, region.top))
        return Rect(top_left.x, top_left.y, region.width, region.height)
