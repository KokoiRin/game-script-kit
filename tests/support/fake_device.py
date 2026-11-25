"""提供测试用输入设备，记录 runner 发出的端口调用。"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_automation.portable.domain import Point
from game_automation.portable.engine.ports import InputDevice


@dataclass(frozen=True, slots=True)
class RecordedAction:
    name: str
    target: Point | None = None
    start: Point | None = None
    end: Point | None = None
    duration_seconds: float | None = None


@dataclass(slots=True)
class FakeInputDevice(InputDevice):
    actions: list[RecordedAction] = field(default_factory=list)

    def click(self, target: Point) -> None:
        """将点击坐标按调用顺序加入 actions，供断言核对窗口换算结果。"""
        self.actions.append(RecordedAction("click", target=target))

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        """将拖拽两端和时长保留为一条 actions 记录，供断言检查完整输入请求。"""
        self.actions.append(
            RecordedAction(
                "drag_to",
                start=start,
                end=end,
                duration_seconds=duration_seconds,
            )
        )

    def wait(self, duration_seconds: float) -> None:
        """将请求的等待时长加入 actions，测试可直接断言等待次数与顺序。"""
        self.actions.append(RecordedAction("wait", duration_seconds=duration_seconds))
