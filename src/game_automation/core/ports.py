"""定义核心层依赖的跨平台端口。"""

from __future__ import annotations

from typing import Protocol

from game_automation.domain import Point


class InputDevice(Protocol):
    def click(self, target: Point) -> None:
        """在屏幕坐标点执行一次跨平台点击。"""

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        """从屏幕起点拖拽到屏幕终点。"""


class PointerPositionReader(Protocol):
    def current_position(self) -> Point:
        """读取当前指针的屏幕坐标。"""


class KeyStateReader(Protocol):
    def is_pressed(self, key: str) -> bool:
        """判断指定按键是否在本轮检测中被触发。"""
