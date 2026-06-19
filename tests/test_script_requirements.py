"""验证脚本运行前端口需求分析。"""

from game_automation.portable.domain import (
    Click,
    Color,
    ColorIs,
    If,
    ImageExists,
    ImageTemplate,
    ImageTarget,
    Point,
    Repeat,
    ScreenWindow,
    Script,
    Wait,
    WaitUntil,
)
from game_automation.portable.engine.script_requirements import inspect_script_requirements


def test_script_requirements_do_not_need_color_reader_for_plain_steps() -> None:
    """验证普通动作和 Repeat 不需要颜色读取端口。"""
    script = Script(
        name="plain",
        window=ScreenWindow(),
        steps=(Repeat(times=2, steps=(Click(Point(1, 2)), Wait(0.1))),),
    )

    requirements = inspect_script_requirements(script)

    assert requirements.needs_color_reader is False
    assert requirements.needs_image_locator is False


def test_script_requirements_need_color_reader_for_color_condition() -> None:
    """验证顶层 If 颜色条件会声明需要取色端口。"""
    script = Script(
        name="color-if",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ColorIs(Point(1, 2), Color(1, 2, 3)),
                then_steps=(Click(Point(3, 4)),),
            ),
        ),
    )

    requirements = inspect_script_requirements(script)

    assert requirements.needs_color_reader is True
    assert requirements.needs_image_locator is False


def test_script_requirements_find_nested_color_condition() -> None:
    """验证需求分析会递归检查嵌套控制流步骤。"""
    nested = If(
        condition=ColorIs(Point(1, 2), Color(1, 2, 3)),
        then_steps=(Click(Point(3, 4)),),
    )
    script = Script(
        name="nested-color-if",
        window=ScreenWindow(),
        steps=(Repeat(times=2, steps=(nested,)),),
    )

    requirements = inspect_script_requirements(script)

    assert requirements.needs_color_reader is True
    assert requirements.needs_image_locator is False


def test_script_requirements_need_color_reader_for_wait_until_color_condition() -> None:
    """验证 WaitUntil 颜色条件会声明需要取色端口。"""
    script = Script(
        name="wait-until-color",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ColorIs(Point(1, 2), Color(1, 2, 3)),
                timeout_seconds=1,
                interval_seconds=0.5,
            ),
        ),
    )

    requirements = inspect_script_requirements(script)

    assert requirements.needs_color_reader is True
    assert requirements.needs_image_locator is False


def test_script_requirements_need_image_locator_for_image_condition() -> None:
    """验证顶层 If 图片条件会声明需要图像定位端口。"""
    script = Script(
        name="image-if",
        window=ScreenWindow(),
        steps=(
            If(
                condition=ImageExists(ImageTemplate("assets/start.png")),
                then_steps=(Click(Point(3, 4)),),
            ),
        ),
    )

    requirements = inspect_script_requirements(script)

    assert requirements.needs_color_reader is False
    assert requirements.needs_image_locator is True


def test_script_requirements_find_nested_image_condition() -> None:
    """验证需求分析会递归检查嵌套图片条件。"""
    nested = If(
        condition=ImageExists(ImageTemplate("assets/start.png")),
        then_steps=(Click(Point(3, 4)),),
    )
    script = Script(
        name="nested-image-if",
        window=ScreenWindow(),
        steps=(Repeat(times=2, steps=(nested,)),),
    )

    requirements = inspect_script_requirements(script)

    assert requirements.needs_image_locator is True


def test_script_requirements_need_image_locator_for_wait_until_image_condition() -> None:
    """验证 WaitUntil 图片条件会声明需要图像定位端口。"""
    script = Script(
        name="wait-until-image",
        window=ScreenWindow(),
        steps=(
            WaitUntil(
                condition=ImageExists(ImageTemplate("assets/start.png")),
                timeout_seconds=1,
                interval_seconds=0.5,
            ),
        ),
    )

    requirements = inspect_script_requirements(script)

    assert requirements.needs_image_locator is True


def test_script_requirements_need_image_locator_for_image_target_click() -> None:
    """验证图片目标点击会声明需要图像定位端口。"""
    script = Script(
        name="click-image",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(ImageTemplate("assets/start.png"))),),
    )

    requirements = inspect_script_requirements(script)

    assert requirements.needs_color_reader is False
    assert requirements.needs_image_locator is True
