"""验证脚本步骤领域模型的基础约束。"""

import pytest

from game_automation.domain import (
    AreaWindow,
    Click,
    Drag,
    Point,
    Rect,
    Repeat,
    ScreenWindow,
    Script,
    Wait,
)


def test_script_preserves_step_order() -> None:
    """验证脚本会保留步骤的原始编排顺序。"""
    steps = (
        Click(Point(1, 2)),
        Drag(Point(3, 4), Point(5, 6), duration_seconds=0.3),
        Wait(0.1),
        Repeat(times=2, steps=(Click(Point(7, 8)),)),
    )

    script = Script(name="demo", window=ScreenWindow(), steps=steps)

    assert script.name == "demo"
    assert script.steps == steps


def test_script_rejects_empty_steps() -> None:
    """验证空脚本会被拒绝。"""
    with pytest.raises(ValueError, match="script requires at least one step"):
        Script(name="empty", window=ScreenWindow(), steps=())


def test_script_rejects_empty_name() -> None:
    """验证空名称和纯空白名称会被拒绝。"""
    steps = (Click(Point(1, 2)),)

    with pytest.raises(ValueError, match="script name cannot be empty"):
        Script(name="", window=ScreenWindow(), steps=steps)

    with pytest.raises(ValueError, match="script name cannot be empty"):
        Script(name="   ", window=ScreenWindow(), steps=steps)


def test_rect_rejects_non_positive_size() -> None:
    """验证非法矩形尺寸会被拒绝。"""
    with pytest.raises(ValueError, match="width"):
        Rect(0, 0, 0, 1)

    with pytest.raises(ValueError, match="height"):
        Rect(0, 0, 1, 0)


def test_actions_do_not_expose_move_or_mouse_button() -> None:
    """验证原子动作步骤没有移动动作和鼠标按键参数。"""
    click = Click(Point(1, 2))
    drag = Drag(Point(1, 2), Point(3, 4))

    assert not hasattr(click, "button")
    assert not hasattr(drag, "button")

    import game_automation.domain.actions as actions

    assert not hasattr(actions, "Move")
    assert not hasattr(actions, "MouseButton")


def test_wait_rejects_negative_duration() -> None:
    """验证等待动作拒绝负数持续时间。"""
    with pytest.raises(ValueError, match="wait duration_seconds"):
        Wait(-0.1)


def test_drag_rejects_negative_duration() -> None:
    """验证拖拽动作拒绝负数持续时间。"""
    with pytest.raises(ValueError, match="drag duration_seconds"):
        Drag(Point(1, 2), Point(3, 4), duration_seconds=-0.1)


def test_script_binds_window_at_script_level() -> None:
    """验证窗口属于脚本，而不是属于单个动作。"""
    window = AreaWindow(Rect(10, 20, 100, 200))
    action = Click(Point(1, 2))
    script = Script(name="area-click", window=window, steps=(action,))

    assert script.window == window
    assert not hasattr(action, "window")


def test_repeat_preserves_times_and_steps() -> None:
    """验证 Repeat 会保留重复次数和内部步骤序列。"""
    steps = (Click(Point(1, 2)), Wait(0.1))

    repeat = Repeat(times=3, steps=steps)

    assert repeat.times == 3
    assert repeat.steps == steps


def test_repeat_rejects_non_positive_times() -> None:
    """验证 Repeat 拒绝非正数重复次数。"""
    steps = (Click(Point(1, 2)),)

    with pytest.raises(ValueError, match="repeat times"):
        Repeat(times=0, steps=steps)

    with pytest.raises(ValueError, match="repeat times"):
        Repeat(times=-1, steps=steps)


def test_repeat_rejects_empty_steps() -> None:
    """验证 Repeat 拒绝空内部步骤。"""
    with pytest.raises(ValueError, match="repeat requires at least one step"):
        Repeat(times=1, steps=())


def test_repeat_allows_nested_steps() -> None:
    """验证 Repeat 允许继续嵌套 Repeat 步骤。"""
    nested = Repeat(times=2, steps=(Click(Point(1, 2)),))
    outer = Repeat(times=3, steps=(nested, Wait(0.1)))

    assert outer.steps == (nested, Wait(0.1))
