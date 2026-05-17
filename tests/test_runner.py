"""验证脚本 runner 会把领域动作映射到输入设备端口。"""

from game_automation.core import AreaWindow, Click, Drag, Point, Rect, Script, ScriptRunner, Wait
from tests.support.fake_device import FakeInputDevice


def test_runner_maps_actions_to_device_with_script_window() -> None:
    """验证 runner 使用脚本级窗口解析点击和拖拽坐标。"""
    device = FakeInputDevice()
    sleeps: list[float] = []
    script = Script(
        name="area-runner",
        window=AreaWindow(Rect(100, 200, 800, 600)),
        actions=(
            Click(Point(10, 20)),
            Drag(Point(30, 40), Point(50, 60), duration_seconds=0.4),
            Wait(0.2),
        ),
    )

    ScriptRunner(device=device, sleeper=sleeps.append).run(script)

    assert [action.name for action in device.actions] == ["click", "drag_to"]
    assert device.actions[0].target == Point(110, 220)
    assert device.actions[1].start == Point(130, 240)
    assert device.actions[1].end == Point(150, 260)
    assert device.actions[1].duration_seconds == 0.4
    assert sleeps == [0.2]
