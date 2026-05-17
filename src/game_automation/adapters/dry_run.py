"""实现 engine.ports.InputDevice — 仅打印操作不真实执行，用于 dry-run 模式。"""

from __future__ import annotations

from game_automation.domain import Point
from game_automation.engine.ports import InputDevice


class DryRunInputDevice(InputDevice):
    def click(self, target: Point) -> None:
        print(f"click {target}")

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        print(f"drag {start} -> {end} (duration={duration_seconds}s)")

    def wait(self, duration_seconds: float) -> None:
        print(f"wait {duration_seconds}s")
