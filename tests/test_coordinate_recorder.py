"""验证坐标记录工具的核心循环行为。"""

from __future__ import annotations

import game_automation.domain.actions as actions
from game_automation.domain import Point
from game_automation.tools.coordinate_recorder import CoordinateRecorder


class FakePointerReader:
    def __init__(self, points: list[Point]) -> None:
        """初始化按顺序返回坐标的 fake reader。"""
        self._points = points
        self.calls = 0

    def current_position(self) -> Point:
        """返回下一条坐标，耗尽后重复最后一条。"""
        point = self._points[min(self.calls, len(self._points) - 1)]
        self.calls += 1
        return point


class FakeKeyReader:
    def __init__(self, states: list[set[str]]) -> None:
        """初始化每轮循环对应的按键状态。"""
        self._states = states
        self.poll_index = 0

    def is_pressed(self, key: str) -> bool:
        """返回当前轮次中指定按键是否按下。"""
        state = self._states[min(self.poll_index, len(self._states) - 1)]
        pressed = key in state
        if key == "Q":
            self.poll_index += 1
        return pressed


class FakeClock:
    def __init__(self) -> None:
        """初始化可控时钟。"""
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        """返回当前 fake 时间。"""
        return self.now

    def sleep(self, seconds: float) -> None:
        """推进 fake 时间并记录 sleep 调用。"""
        self.sleeps.append(seconds)
        self.now += seconds


def test_display_interval_does_not_block_key_polling() -> None:
    """验证坐标显示每秒一次，同时按键检测每 50ms 一次。"""
    states = [set() for _ in range(20)] + [{"Q"}]
    pointer = FakePointerReader([Point(1, 1), Point(2, 2)])
    keys = FakeKeyReader(states)
    clock = FakeClock()
    outputs: list[str] = []

    recorder = CoordinateRecorder(
        pointer_reader=pointer,
        key_reader=keys,
        sleeper=clock.sleep,
        clock=clock,
        output=outputs.append,
    )

    recorder.run()

    assert outputs.count("current: Point(x=1, y=1)") == 1
    assert outputs.count("current: Point(x=2, y=2)") == 1
    assert clock.sleeps == [0.05] * 20


def test_holding_one_records_only_once() -> None:
    """验证长按 1 只记录一次坐标。"""
    pointer = FakePointerReader([Point(0, 0), Point(10, 10), Point(20, 20)])
    keys = FakeKeyReader([{"1"}, {"1"}, {"1"}, {"Q"}])
    clock = FakeClock()
    outputs: list[str] = []

    recorded = CoordinateRecorder(
        pointer_reader=pointer,
        key_reader=keys,
        sleeper=clock.sleep,
        clock=clock,
        output=outputs.append,
    ).run()

    assert recorded == (Point(10, 10),)
    assert outputs.count("recorded: Point(x=10, y=10)") == 1


def test_record_rereads_latest_position_and_q_exits_quickly() -> None:
    """验证按 1 会重新读取最新坐标，按 q 会快速退出。"""
    pointer = FakePointerReader([Point(1, 1), Point(9, 9)])
    keys = FakeKeyReader([{"1", "q"}])
    clock = FakeClock()
    outputs: list[str] = []

    recorded = CoordinateRecorder(
        pointer_reader=pointer,
        key_reader=keys,
        sleeper=clock.sleep,
        clock=clock,
        output=outputs.append,
    ).run()

    assert recorded == (Point(9, 9),)
    assert pointer.calls == 2
    assert clock.sleeps == []


def test_recorder_does_not_add_script_actions() -> None:
    """验证工具没有向脚本动作模型添加获取坐标动作。"""
    assert not hasattr(actions, "GetCoordinate")
    assert not hasattr(actions, "RecordCoordinate")
