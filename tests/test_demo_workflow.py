"""验证核心 demo workflow 的平台无关行为。"""

from game_automation.core import build_demo_script, run_demo_workflow
from game_automation.domain import Point
from tests.support.fake_device import FakeInputDevice


def test_demo_workflow_records_expected_operation_order() -> None:
    """验证 demo workflow 会通过脚本模型请求点击和拖动。"""
    device = FakeInputDevice()
    sleeps: list[float] = []

    run_demo_workflow(device, sleeper=sleeps.append)

    assert [action.name for action in device.actions] == ["click", "drag_to"]
    assert device.actions[0].target == Point(300, 300)
    assert device.actions[1].start == Point(300, 300)
    assert device.actions[1].end == Point(460, 360)
    assert sleeps == [0.1]


def test_demo_workflow_builds_script() -> None:
    """验证 demo workflow 使用脚本领域模型表达固定动作序列。"""
    script = build_demo_script()

    assert script.name == "demo"
    assert len(script.actions) == 3


def test_core_import_does_not_import_macos_adapter() -> None:
    """验证导入 core 不会顺带导入 macOS adapter。"""
    import sys

    sys.modules.pop("game_automation.adapters.macos", None)

    import game_automation.core  # noqa: F401

    assert "game_automation.adapters.macos" not in sys.modules
