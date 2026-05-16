"""定义核心层依赖的跨平台输入设备端口。"""

from __future__ import annotations

from typing import Protocol

from game_automation.core.geometry import Point


class InputDevice(Protocol):
    def click(self, target: Point) -> None:
        """在屏幕坐标点执行一次跨平台点击。"""

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        """从屏幕起点拖拽到屏幕终点。"""
