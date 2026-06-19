"""验证脚本步骤领域模型的基础约束。"""

import pytest

from game_automation.portable.domain import (
    AreaWindow,
    Click,
    Color,
    ColorIs,
    Drag,
    If,
    ImageExists,
    ImageTemplate,
    ImageTarget,
    Point,
    Rect,
    Repeat,
    ScreenWindow,
    Script,
    Wait,
    WaitUntil,
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

    import game_automation.portable.domain.actions as actions

    assert not hasattr(actions, "Move")
    assert not hasattr(actions, "MouseButton")


def test_image_target_preserves_template_and_defaults() -> None:
    """验证图片目标会保留模板并默认点击匹配中心。"""
    target = ImageTarget(ImageTemplate("assets/start.png"))

    assert target.template == ImageTemplate("assets/start.png")
    assert target.region is None
    assert target.min_confidence == 1.0
    assert target.offset == Point(0, 0)


def test_image_target_preserves_region_confidence_and_offset() -> None:
    """验证图片目标会保留搜索区域、置信度和中心偏移。"""
    target = ImageTarget(
        ImageTemplate("assets/start.png"),
        region=Rect(10, 20, 30, 40),
        min_confidence=0.8,
        offset=Point(5, -3),
    )

    assert target.region == Rect(10, 20, 30, 40)
    assert target.min_confidence == 0.8
    assert target.offset == Point(5, -3)


@pytest.mark.parametrize("min_confidence", [0.0, -0.1, 1.1])
def test_image_target_rejects_invalid_min_confidence(min_confidence: float) -> None:
    """验证图片目标拒绝非法最低匹配置信度。"""
    with pytest.raises(ValueError, match="image target min_confidence"):
        ImageTarget(
            ImageTemplate("assets/start.png"),
            min_confidence=min_confidence,
        )


def test_click_preserves_image_target() -> None:
    """验证 Click 可以保存图片目标。"""
    target = ImageTarget(ImageTemplate("assets/start.png"))

    assert Click(target).point == target


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


def test_color_condition_preserves_point_color_and_tolerance() -> None:
    """验证颜色条件会保留点位、期望颜色和容差。"""
    condition = ColorIs(
        point=Point(10, 20),
        expected=Color.from_hex("#112233"),
        tolerance=7,
    )

    assert condition.point == Point(10, 20)
    assert condition.expected == Color(17, 34, 51)
    assert condition.tolerance == 7


def test_color_condition_defaults_to_exact_match() -> None:
    """验证颜色条件默认使用精确匹配。"""
    condition = ColorIs(point=Point(1, 2), expected=Color(1, 2, 3))

    assert condition.tolerance == 0


def test_color_condition_rejects_invalid_tolerance() -> None:
    """验证颜色条件拒绝非法容差。"""
    with pytest.raises(ValueError, match="color tolerance"):
        ColorIs(point=Point(1, 2), expected=Color(1, 2, 3), tolerance=-1)

    with pytest.raises(ValueError, match="color tolerance"):
        ColorIs(point=Point(1, 2), expected=Color(1, 2, 3), tolerance=256)


def test_image_exists_condition_preserves_template_and_defaults() -> None:
    """验证图片存在条件会保留模板并默认全屏精确匹配。"""
    condition = ImageExists(template=ImageTemplate("assets/start.png"))

    assert condition.template == ImageTemplate("assets/start.png")
    assert condition.region is None
    assert condition.min_confidence == 1.0


def test_image_exists_condition_preserves_region_and_min_confidence() -> None:
    """验证图片存在条件会保留搜索区域和最低匹配置信度。"""
    condition = ImageExists(
        template=ImageTemplate("assets/start.png"),
        region=Rect(left=10, top=20, width=30, height=40),
        min_confidence=0.8,
    )

    assert condition.region == Rect(left=10, top=20, width=30, height=40)
    assert condition.min_confidence == 0.8


@pytest.mark.parametrize("min_confidence", [0.0, -0.1, 1.1])
def test_image_exists_condition_rejects_invalid_min_confidence(
    min_confidence: float,
) -> None:
    """验证图片存在条件拒绝非法最低匹配置信度。"""
    with pytest.raises(ValueError, match="image exists min_confidence"):
        ImageExists(
            template=ImageTemplate("assets/start.png"),
            min_confidence=min_confidence,
        )


def test_if_preserves_condition_and_branch_steps() -> None:
    """验证 If 会保留条件和两个分支步骤序列。"""
    condition = ColorIs(point=Point(1, 2), expected=Color(1, 2, 3))
    then_steps = (Click(Point(3, 4)),)
    else_steps = (Wait(0.5),)

    branch = If(condition=condition, then_steps=then_steps, else_steps=else_steps)

    assert branch.condition == condition
    assert branch.then_steps == then_steps
    assert branch.else_steps == else_steps


def test_if_rejects_empty_then_steps() -> None:
    """验证 If 拒绝空 then 分支。"""
    condition = ColorIs(point=Point(1, 2), expected=Color(1, 2, 3))

    with pytest.raises(ValueError, match="if requires at least one then step"):
        If(condition=condition, then_steps=())


def test_if_allows_empty_else_steps() -> None:
    """验证 If 允许省略 else 分支。"""
    condition = ColorIs(point=Point(1, 2), expected=Color(1, 2, 3))
    branch = If(condition=condition, then_steps=(Click(Point(3, 4)),))

    assert branch.else_steps == ()


def test_if_allows_nested_control_flow_steps() -> None:
    """验证 If 分支内允许嵌套控制流步骤。"""
    condition = ColorIs(point=Point(1, 2), expected=Color(1, 2, 3))
    nested = If(condition=condition, then_steps=(Wait(0.1),))
    repeat = Repeat(times=2, steps=(nested,))

    branch = If(condition=condition, then_steps=(repeat,), else_steps=(nested,))

    assert branch.then_steps == (repeat,)
    assert branch.else_steps == (nested,)


def test_wait_until_preserves_condition_timeout_and_interval() -> None:
    """验证 WaitUntil 会保留条件、超时和轮询间隔。"""
    condition = ColorIs(point=Point(1, 2), expected=Color(1, 2, 3))

    wait_until = WaitUntil(
        condition=condition,
        timeout_seconds=5,
        interval_seconds=0.5,
    )

    assert wait_until.condition == condition
    assert wait_until.timeout_seconds == 5
    assert wait_until.interval_seconds == 0.5


def test_wait_until_rejects_non_positive_timeout() -> None:
    """验证 WaitUntil 拒绝非正数超时时间。"""
    condition = ColorIs(point=Point(1, 2), expected=Color(1, 2, 3))

    with pytest.raises(ValueError, match="wait until timeout_seconds"):
        WaitUntil(condition=condition, timeout_seconds=0, interval_seconds=0.5)

    with pytest.raises(ValueError, match="wait until timeout_seconds"):
        WaitUntil(condition=condition, timeout_seconds=-1, interval_seconds=0.5)


def test_wait_until_rejects_non_positive_interval() -> None:
    """验证 WaitUntil 拒绝非正数轮询间隔。"""
    condition = ColorIs(point=Point(1, 2), expected=Color(1, 2, 3))

    with pytest.raises(ValueError, match="wait until interval_seconds"):
        WaitUntil(condition=condition, timeout_seconds=5, interval_seconds=0)

    with pytest.raises(ValueError, match="wait until interval_seconds"):
        WaitUntil(condition=condition, timeout_seconds=5, interval_seconds=-0.1)


def test_wait_until_allows_nested_control_flow_steps() -> None:
    """验证 WaitUntil 可以嵌套在 Repeat 或 If 的内部步骤中。"""
    condition = ColorIs(point=Point(1, 2), expected=Color(1, 2, 3))
    wait_until = WaitUntil(condition=condition, timeout_seconds=5, interval_seconds=0.5)

    repeat = Repeat(times=2, steps=(wait_until,))
    branch = If(condition=condition, then_steps=(wait_until,))

    assert repeat.steps == (wait_until,)
    assert branch.then_steps == (wait_until,)
