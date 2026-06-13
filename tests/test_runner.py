"""验证脚本 runner 会把领域步骤映射到输入设备端口。"""

import pytest

from game_automation.portable.engine.runner import ScriptRunner
from game_automation.portable.domain import (
    AreaWindow,
    Click,
    Color,
    ColorIs,
    Drag,
    If,
    Point,
    Rect,
    Repeat,
    ScreenWindow,
    Script,
    Wait,
    WaitUntil,
)
from tests.support.fake_device import FakeInputDevice


class FakeColorReader:
    """提供 runner 测试用固定取色结果。"""

    def __init__(self, color: Color) -> None:
        """保存固定颜色并记录读取点。"""
        self.color = color
        self.points: list[Point] = []

    def read_color(self, point: Point) -> Color:
        """记录读取点并返回固定颜色。"""
        self.points.append(point)
        return self.color


class SequenceColorReader:
    """按序返回颜色，序列耗尽后保持最后一个颜色。"""

    def __init__(self, colors: list[Color]) -> None:
        """保存颜色序列并记录读取点。"""
        self.colors = colors
        self.points: list[Point] = []

    def read_color(self, point: Point) -> Color:
        """返回下一个颜色并记录读取点。"""
        self.points.append(point)
        index = min(len(self.points) - 1, len(self.colors) - 1)
        return self.colors[index]


def test_runner_maps_steps_to_device_with_script_window() -> None:
    """验证 runner 使用脚本级窗口解析点击和拖拽坐标。"""
    device = FakeInputDevice()
    script = Script(
        name="area-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            Click(Point(10, 20)),
            Drag(Point(30, 40), Point(50, 60), duration_seconds=0.4),
            Wait(0.2),
        ),
    )

    ScriptRunner(device=device).run(script)

    assert [action.name for action in device.actions] == ["click", "drag_to", "wait"]
    assert device.actions[0].target == Point(110, 220)
    assert device.actions[1].start == Point(130, 240)
    assert device.actions[1].end == Point(150, 260)
    assert device.actions[1].duration_seconds == 0.4
    assert device.actions[2].duration_seconds == 0.2


def test_runner_expands_repeat_steps() -> None:
    """验证 runner 会按固定次数展开 Repeat 内部步骤。"""
    device = FakeInputDevice()
    script = Script(
        name="repeat-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            Repeat(
                times=3,
                steps=(
                    Click(Point(10, 20)),
                    Wait(0.5),
                ),
            ),
        ),
    )

    ScriptRunner(device=device).run(script)

    assert [action.name for action in device.actions] == [
        "click",
        "wait",
        "click",
        "wait",
        "click",
        "wait",
    ]
    assert [action.target for action in device.actions if action.name == "click"] == [
        Point(110, 220),
        Point(110, 220),
        Point(110, 220),
    ]


def test_runner_expands_nested_repeat_steps_with_script_window() -> None:
    """验证 runner 会递归展开嵌套 Repeat 并保留窗口坐标解析。"""
    device = FakeInputDevice()
    script = Script(
        name="nested-repeat-runner",
        window=AreaWindow(Rect(10, 20, 800, 600)),
        steps=(
            Repeat(
                times=2,
                steps=(
                    Click(Point(1, 2)),
                    Repeat(times=2, steps=(Drag(Point(3, 4), Point(5, 6)),)),
                ),
            ),
        ),
    )

    ScriptRunner(device=device).run(script)

    assert [action.name for action in device.actions] == [
        "click",
        "drag_to",
        "drag_to",
        "click",
        "drag_to",
        "drag_to",
    ]
    assert device.actions[0].target == Point(11, 22)
    assert device.actions[1].start == Point(13, 24)
    assert device.actions[1].end == Point(15, 26)
    assert device.actions[4].start == Point(13, 24)
    assert device.actions[4].end == Point(15, 26)


def test_runner_executes_then_branch_when_color_condition_matches() -> None:
    """验证颜色条件为真时 runner 只执行 then 分支。"""
    device = FakeInputDevice()
    color_reader = FakeColorReader(Color(10, 20, 30))
    script = Script(
        name="if-then-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                then_steps=(Click(Point(3, 4)),),
                else_steps=(Click(Point(5, 6)),),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=color_reader).run(script)

    assert [action.name for action in device.actions] == ["click"]
    assert device.actions[0].target == Point(103, 204)


def test_runner_executes_else_branch_when_color_condition_does_not_match() -> None:
    """验证颜色条件为假时 runner 只执行 else 分支。"""
    device = FakeInputDevice()
    script = Script(
        name="if-else-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                then_steps=(Click(Point(3, 4)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(99, 20, 30))).run(script)

    assert [action.name for action in device.actions] == ["wait"]
    assert device.actions[0].duration_seconds == 0.5


def test_runner_skips_empty_else_branch_and_continues() -> None:
    """验证空 else 分支不会发起操作且后续步骤继续执行。"""
    device = FakeInputDevice()
    script = Script(
        name="if-empty-else-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                then_steps=(Click(Point(3, 4)),),
            ),
            Wait(1),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(0, 0, 0))).run(script)

    assert [action.name for action in device.actions] == ["wait"]
    assert device.actions[0].duration_seconds == 1


def test_runner_resolves_color_condition_point_with_script_window() -> None:
    """验证颜色条件点会使用脚本窗口解析为屏幕坐标。"""
    device = FakeInputDevice()
    color_reader = FakeColorReader(Color(1, 2, 3))
    script = Script(
        name="if-window-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            If(
                condition=ColorIs(Point(7, 8), Color(1, 2, 3)),
                then_steps=(Wait(0.1),),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=color_reader).run(script)

    assert color_reader.points == [Point(107, 208)]


def test_runner_matches_color_condition_with_channel_tolerance() -> None:
    """验证颜色条件按每个 RGB 通道容差匹配。"""
    device = FakeInputDevice()
    script = Script(
        name="if-tolerance-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30), tolerance=2),
                then_steps=(Click(Point(3, 4)),),
                else_steps=(Wait(0.5),),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(12, 18, 31))).run(script)

    assert [action.name for action in device.actions] == ["click"]


def test_runner_requires_color_reader_for_color_condition() -> None:
    """验证执行颜色条件时必须注入颜色读取端口。"""
    script = Script(
        name="if-missing-reader-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                then_steps=(Click(Point(3, 4)),),
            ),
        ),
    )

    with pytest.raises(RuntimeError, match="color reader"):
        ScriptRunner(device=FakeInputDevice()).run(script)


def test_runner_executes_nested_if_and_repeat_steps() -> None:
    """验证 runner 能递归解释嵌套 If 和 Repeat。"""
    device = FakeInputDevice()
    matching_condition = ColorIs(Point(1, 2), Color(10, 20, 30))
    script = Script(
        name="nested-if-repeat-runner",
        window=ScreenWindow(),
        steps=(
            If(
                condition=matching_condition,
                then_steps=(
                    Repeat(
                        times=2,
                        steps=(
                            If(
                                condition=matching_condition,
                                then_steps=(Click(Point(3, 4)),),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(10, 20, 30))).run(script)

    assert [action.name for action in device.actions] == ["click", "click"]


def test_runner_wait_until_continues_immediately_when_condition_matches() -> None:
    """验证 WaitUntil 初始条件满足时不等待并继续后续步骤。"""
    device = FakeInputDevice()
    script = Script(
        name="wait-until-immediate",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                timeout_seconds=5,
                interval_seconds=0.5,
            ),
            Click(Point(3, 4)),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(10, 20, 30))).run(script)

    assert [action.name for action in device.actions] == ["click"]
    assert device.actions[0].target == Point(3, 4)


def test_runner_wait_until_waits_until_condition_matches() -> None:
    """验证 WaitUntil 会按间隔等待直到条件满足。"""
    device = FakeInputDevice()
    color_reader = SequenceColorReader(
        [
            Color(0, 0, 0),
            Color(0, 0, 0),
            Color(10, 20, 30),
        ]
    )
    script = Script(
        name="wait-until-eventual",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        steps=(
            WaitUntil(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                timeout_seconds=5,
                interval_seconds=0.5,
            ),
            Click(Point(3, 4)),
        ),
    )

    ScriptRunner(device=device, color_reader=color_reader).run(script)

    assert [action.name for action in device.actions] == ["wait", "wait", "click"]
    assert [action.duration_seconds for action in device.actions if action.name == "wait"] == [0.5, 0.5]
    assert device.actions[-1].target == Point(103, 204)
    assert color_reader.points == [Point(101, 202), Point(101, 202), Point(101, 202)]


def test_runner_wait_until_times_out_and_stops_following_steps() -> None:
    """验证 WaitUntil 超时后抛错且不执行后续步骤。"""
    device = FakeInputDevice()
    script = Script(
        name="wait-until-timeout",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                timeout_seconds=1,
                interval_seconds=0.5,
            ),
            Click(Point(3, 4)),
        ),
    )

    with pytest.raises(TimeoutError, match="wait until condition timed out"):
        ScriptRunner(device=device, color_reader=FakeColorReader(Color(0, 0, 0))).run(script)

    assert [action.name for action in device.actions] == ["wait", "wait"]
    assert [action.duration_seconds for action in device.actions] == [0.5, 0.5]


def test_runner_wait_until_caps_wait_to_remaining_timeout() -> None:
    """验证 WaitUntil 最后一轮等待不会超过剩余超时预算。"""
    device = FakeInputDevice()
    script = Script(
        name="wait-until-remaining-budget",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ColorIs(Point(1, 2), Color(10, 20, 30)),
                timeout_seconds=1,
                interval_seconds=0.6,
            ),
        ),
    )

    with pytest.raises(TimeoutError):
        ScriptRunner(device=device, color_reader=FakeColorReader(Color(0, 0, 0))).run(script)

    assert [action.duration_seconds for action in device.actions] == [0.6, 0.4]


def test_runner_wait_until_executes_inside_nested_control_flow() -> None:
    """验证 WaitUntil 可在嵌套控制流中执行。"""
    device = FakeInputDevice()
    condition = ColorIs(Point(1, 2), Color(10, 20, 30))
    script = Script(
        name="wait-until-nested",
        window=ScreenWindow(),
        steps=(
            If(
                condition=condition,
                then_steps=(
                    Repeat(
                        times=2,
                        steps=(
                            WaitUntil(
                                condition=condition,
                                timeout_seconds=1,
                                interval_seconds=0.5,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    ScriptRunner(device=device, color_reader=FakeColorReader(Color(10, 20, 30))).run(script)

    assert device.actions == []


def test_engine_import_does_not_import_macos_adapter() -> None:
    """验证导入 engine 不会顺带导入 macOS adapter。"""
    import sys

    sys.modules.pop("game_automation.platform.macos.adapters", None)

    import game_automation.portable.engine  # noqa: F401

    assert "game_automation.platform.macos.adapters" not in sys.modules
