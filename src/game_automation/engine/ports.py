"""定义执行引擎的跨平台端口。"""

from __future__ import annotations

from typing import Protocol

from game_automation.domain import Color, Point


class InputDevice(Protocol):
    def click(self, target: Point) -> None:
        """在屏幕坐标点执行一次跨平台点击。"""

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        """从屏幕起点拖拽到屏幕终点。"""

    def wait(self, duration_seconds: float) -> None:
        """等待指定秒数。"""


class PointerPositionReader(Protocol):
    def current_position(self) -> Point:
        """读取当前指针的屏幕坐标。"""


class PixelColorReader(Protocol):
    def read_color(self, point: Point) -> Color:
        """读取指定屏幕坐标点的 RGB 颜色。"""
        ...


class KeyStateReader(Protocol):
    def is_pressed(self, key: str) -> bool:
        """判断指定按键是否在本轮检测中被触发。"""
