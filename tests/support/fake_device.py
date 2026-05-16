"""提供测试用输入设备，记录 runner 发出的端口调用。"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_automation.core import Point


@dataclass(frozen=True, slots=True)
class RecordedAction:
    name: str
    target: Point | None = None
    start: Point | None = None
    end: Point | None = None
    duration_seconds: float | None = None


@dataclass(slots=True)
class FakeInputDevice:
    actions: list[RecordedAction] = field(default_factory=list)

    def click(self, target: Point) -> None:
        """记录一次点击请求。"""
        self.actions.append(RecordedAction("click", target=target))

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        """记录一次拖拽请求。"""
        self.actions.append(
            RecordedAction(
                "drag_to",
                start=start,
                end=end,
                duration_seconds=duration_seconds,
            )
        )
