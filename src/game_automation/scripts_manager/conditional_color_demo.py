"""保存用于验证颜色条件分支行为的命名脚本。"""

from __future__ import annotations

from game_automation.domain import Click, Color, ColorIs, If, Point, ScreenWindow, Script, Wait


CONDITIONAL_COLOR_DEMO_SCRIPT = Script(
    name="conditional-color-demo",
    window=ScreenWindow(),
    steps=(
        If(
            condition=ColorIs(
                point=Point(50, 60),
                expected=Color.from_hex("#102030"),
                tolerance=0,
            ),
            then_steps=(
                Click(Point(100, 200)),
                Wait(0.25),
            ),
            else_steps=(
                Click(Point(300, 400)),
                Wait(0.5),
            ),
        ),
    ),
)


def build_conditional_color_demo_script() -> Script:
    """返回用于 dry-run 验证颜色条件分支的命名脚本。"""
    return CONDITIONAL_COLOR_DEMO_SCRIPT
