"""保存可编辑的 demo 命名脚本定义。"""

from __future__ import annotations

from game_automation.core.actions import Click, Drag, Wait
from game_automation.core.geometry import Point
from game_automation.core.script import Script
from game_automation.core.windows import ScreenWindow


DEMO_SCRIPT = Script(
    name="demo",
    window=ScreenWindow(),
    actions=(
        Click(Point(300, 300)),
        Drag(Point(300, 300), Point(460, 360), duration_seconds=0.4),
        Wait(0.1),
    ),
)


def build_demo_script() -> Script:
    """返回可重复使用的 demo 命名脚本。"""
    return DEMO_SCRIPT
