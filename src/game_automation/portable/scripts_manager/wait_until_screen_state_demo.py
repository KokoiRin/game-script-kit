"""保存用于验证界面状态条件等待行为的命名脚本。

本 module 只声明一份内置脚本数据；它不执行状态探测、不推进等待时间，
也不处理超时错误。
"""

from __future__ import annotations

from game_automation.portable.domain import Click, Point, ScreenStateIs, ScreenWindow, Script, WaitUntil


WAIT_UNTIL_SCREEN_STATE_DEMO_SCRIPT = Script(
    name="wait-until-screen-state-demo",
    window=ScreenWindow(),
    steps=(
        WaitUntil(
            condition=ScreenStateIs("主页"),
            timeout_seconds=1,
            interval_seconds=0.5,
        ),
        Click(Point(100, 200)),
    ),
)


def build_wait_until_screen_state_demo_script() -> Script:
    """返回用于 dry-run 验证界面状态等待的命名脚本。"""
    return WAIT_UNTIL_SCREEN_STATE_DEMO_SCRIPT
