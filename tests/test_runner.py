"""验证脚本 runner 会把领域步骤映射到输入设备端口。"""

from game_automation.engine.runner import ScriptRunner
from game_automation.domain import AreaWindow, Click, Drag, Point, Rect, Repeat, Script, Wait
from tests.support.fake_device import FakeInputDevice


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


def test_engine_import_does_not_import_macos_adapter() -> None:
    """验证导入 engine 不会顺带导入 macOS adapter。"""
    import sys

    sys.modules.pop("game_automation.adapters.macos", None)

    import game_automation.engine  # noqa: F401

    assert "game_automation.adapters.macos" not in sys.modules
