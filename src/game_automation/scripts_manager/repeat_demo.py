"""保存用于验证 Repeat 步骤展开行为的命名脚本。

本 module 只声明一份内置脚本数据；它不展开 Repeat，也不调用运行端口。
"""

from __future__ import annotations

from game_automation.domain import Click, Point, Repeat, ScreenWindow, Script, Wait


REPEAT_DEMO_SCRIPT = Script(
    name="repeat-demo",
    window=ScreenWindow(),
    steps=(
        Wait(2),
        Repeat(
            times=5,
            steps=(
                Click(Point(120, 180)),
                Wait(1),
            ),
        ),
    ),
)


def build_repeat_demo_script() -> Script:
    """返回用于 dry-run 验证 Repeat 的命名脚本。"""
    return REPEAT_DEMO_SCRIPT
