"""实现 demo 脚本构造，展示核心逻辑如何通过脚本模型运行。"""

from __future__ import annotations

import time

from game_automation.core.actions import Click, Drag, Wait
from game_automation.core.geometry import Point
from game_automation.core.ports import InputDevice
from game_automation.core.runner import Sleeper, ScriptRunner
from game_automation.core.script import Script
from game_automation.core.windows import ScreenWindow


DEMO_SCRIPT = Script(
    window=ScreenWindow(),
    actions=(
        Click(Point(300, 300)),
        Drag(Point(300, 300), Point(460, 360), duration_seconds=0.4),
        Wait(0.1),
    ),
)


def build_demo_script() -> Script:
    """构造一个可重复使用的最小 demo 脚本。"""
    return DEMO_SCRIPT


def run_demo_workflow(device: InputDevice, sleeper: Sleeper = time.sleep) -> None:
    """运行基于脚本模型的 demo workflow。"""
    ScriptRunner(device=device, sleeper=sleeper).run(build_demo_script())
