"""验证脚本动作领域模型的基础约束。"""

import pytest

from game_automation.core import AreaWindow, Click, Drag, Point, Rect, ScreenWindow, Script, Wait


def test_script_preserves_action_order() -> None:
    """验证脚本会保留动作的原始编排顺序。"""
    actions = (
        Click(Point(1, 2)),
        Drag(Point(3, 4), Point(5, 6), duration_seconds=0.3),
        Wait(0.1),
    )

    script = Script(name="demo", window=ScreenWindow(), actions=actions)

    assert script.name == "demo"
    assert script.actions == actions


def test_script_rejects_empty_actions() -> None:
    """验证空脚本会被拒绝。"""
    with pytest.raises(ValueError, match="script requires at least one action"):
        Script(name="empty", window=ScreenWindow(), actions=())


def test_script_rejects_empty_name() -> None:
    """验证空名称和纯空白名称会被拒绝。"""
    actions = (Click(Point(1, 2)),)

    with pytest.raises(ValueError, match="script name cannot be empty"):
        Script(name="", window=ScreenWindow(), actions=actions)

    with pytest.raises(ValueError, match="script name cannot be empty"):
        Script(name="   ", window=ScreenWindow(), actions=actions)


def test_rect_rejects_non_positive_size() -> None:
    """验证非法矩形尺寸会被拒绝。"""
    with pytest.raises(ValueError, match="width"):
        Rect(0, 0, 0, 1)

    with pytest.raises(ValueError, match="height"):
        Rect(0, 0, 1, 0)


def test_actions_do_not_expose_move_or_mouse_button() -> None:
    """验证第一版动作模型没有移动动作和鼠标按键参数。"""
    click = Click(Point(1, 2))
    drag = Drag(Point(1, 2), Point(3, 4))

    assert not hasattr(click, "button")
    assert not hasattr(drag, "button")

    import game_automation.core.actions as actions

    assert not hasattr(actions, "Move")
    assert not hasattr(actions, "MouseButton")


def test_script_binds_window_at_script_level() -> None:
    """验证窗口属于脚本，而不是属于单个动作。"""
    window = AreaWindow(Rect(10, 20, 100, 200))
    action = Click(Point(1, 2))
    script = Script(name="area-click", window=window, actions=(action,))

    assert script.window == window
    assert not hasattr(action, "window")
