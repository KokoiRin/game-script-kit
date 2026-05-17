"""验证基于已记录坐标的点击脚本。"""

from game_automation.core import build_recorded_click_script, run_recorded_click_script
from game_automation.domain import Point
from tests.support.fake_device import FakeInputDevice


def test_recorded_click_script_contains_requested_sequence() -> None:
    """验证脚本按用户记录的坐标和等待时间编排。"""
    script = build_recorded_click_script()

    assert script.name == "recorded-clicks"
    assert [type(action).__name__ for action in script.actions] == [
        "Wait",
        "Click",
        "Wait",
        "Click",
        "Wait",
        "Click",
    ]
    assert script.actions[0].duration_seconds == 3
    assert script.actions[1].point == Point(242, 92)
    assert script.actions[2].duration_seconds == 3
    assert script.actions[3].point == Point(736, 323)
    assert script.actions[4].duration_seconds == 10
    assert script.actions[5].point == Point(741, 400)


def test_recorded_click_script_runs_through_ports() -> None:
    """验证运行脚本时只通过输入设备端口执行点击。"""
    device = FakeInputDevice()
    sleeps: list[float] = []

    run_recorded_click_script(device, sleeper=sleeps.append)

    assert [action.target for action in device.actions] == [
        Point(242, 92),
        Point(736, 323),
        Point(741, 400),
    ]
    assert sleeps == [3, 3, 10]
