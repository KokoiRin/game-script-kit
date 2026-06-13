"""实现 dry-run adapter。

本 module 只把输入动作打印到 stdout，并为条件脚本提供固定取色结果；
它不执行真实鼠标动作，也不决定 dry-run 模式何时启用。
"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.portable.domain import Color, Point
from game_automation.portable.engine.ports import InputDevice, PixelColorReader


class DryRunInputDevice(InputDevice):
    def click(self, target: Point) -> None:
        print(f"click {target}")

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        print(f"drag {start} -> {end} (duration={duration_seconds}s)")

    def wait(self, duration_seconds: float) -> None:
        print(f"wait {duration_seconds}s")


@dataclass(frozen=True, slots=True)
class DryRunPixelColorReader(PixelColorReader):
    color: Color

    def read_color(self, point: Point) -> Color:
        """返回固定颜色，让 dry-run 条件分支可预测。"""
        return self.color
