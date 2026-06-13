"""保存可编辑的 demo 命名脚本定义。

本 module 只声明一份内置脚本数据；它不执行脚本，也不包含运行模式判断。
"""

from __future__ import annotations

from game_automation.domain import Click, Drag, Point, ScreenWindow, Script, Wait


DEMO_SCRIPT = Script(
    name="demo",
    window=ScreenWindow(),
    steps=(
        Click(Point(300, 300)),
        Drag(Point(300, 300), Point(460, 360), duration_seconds=0.4),
        Wait(0.1),
    ),
)


def build_demo_script() -> Script:
    """返回可重复使用的 demo 命名脚本。"""
    return DEMO_SCRIPT
