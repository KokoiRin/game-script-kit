"""定义任务窗口，以及窗口内坐标到已绑定窗口屏幕位置的解析规则。

本 module 只负责坐标解析；它不读写真实窗口，也不选择或激活应用。
真实运行由原生窗口会话提供 AreaWindow。未绑定窗口只用于不接触桌面的 dry-run。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from game_automation.portable.domain.geometry import Point, Rect


class Window(Protocol):
    def resolve(self, point: Point) -> Point:
        """把窗口内点解析为本次运行使用的坐标点。"""

    def resolve_region(self, region: Rect | None) -> Rect | None:
        """把可选窗口内区域解析为本次运行的图片搜索区域。"""


@dataclass(frozen=True, slots=True)
class UnboundWindow:
    """dry-run 没有活动窗口时按作者写下的窗口相对坐标原样传递。"""

    def resolve(self, point: Point) -> Point:
        """不把点位映射到屏幕，避免 dry-run 引入第二套绝对坐标。"""
        return point

    def resolve_region(self, region: Rect | None) -> Rect | None:
        """保留作者声明的搜索区域；没有区域时不扩展成整屏。"""
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
