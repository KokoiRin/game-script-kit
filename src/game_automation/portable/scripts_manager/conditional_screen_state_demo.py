"""保存用于验证界面状态条件分支行为的命名脚本。

本 module 只声明一份内置脚本数据；它不识别真实界面状态，也不读取状态配置。
"""

from __future__ import annotations

from game_automation.portable.domain import Click, If, Point, ScreenStateIs, ScreenWindow, Script, Wait


CONDITIONAL_SCREEN_STATE_DEMO_SCRIPT = Script(
    name="conditional-screen-state-demo",
    window=ScreenWindow(),
    steps=(
        If(
            condition=ScreenStateIs("主页"),
            then_steps=(Click(Point(100, 200)),),
            else_steps=(Wait(0.5),),
        ),
    ),
)


def build_conditional_screen_state_demo_script() -> Script:
    """返回用于 dry-run 验证界面状态条件分支的命名脚本。"""
    return CONDITIONAL_SCREEN_STATE_DEMO_SCRIPT
