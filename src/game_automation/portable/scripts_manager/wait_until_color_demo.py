"""保存用于验证条件等待行为的命名脚本。

本 module 只声明一份内置脚本数据；它不轮询条件、不推进等待时间，
也不处理超时错误。
"""

from __future__ import annotations

from game_automation.portable.domain import Click, Color, ColorIs, Point, ScreenWindow, Script, WaitUntil


WAIT_UNTIL_COLOR_DEMO_SCRIPT = Script(
    name="wait-until-color-demo",
    window=ScreenWindow(),
    steps=(
        WaitUntil(
            condition=ColorIs(
                point=Point(50, 60),
                expected=Color.from_hex("#102030"),
                tolerance=0,
            ),
            timeout_seconds=1,
            interval_seconds=0.5,
        ),
        Click(Point(100, 200)),
    ),
)


def build_wait_until_color_demo_script() -> Script:
    """返回用于 dry-run 验证条件等待的命名脚本。"""
    return WAIT_UNTIL_COLOR_DEMO_SCRIPT
