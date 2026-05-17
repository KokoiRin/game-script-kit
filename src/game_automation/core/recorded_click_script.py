"""定义基于已记录坐标的点击脚本。"""

from __future__ import annotations

import time

from game_automation.core.actions import Click, Wait
from game_automation.core.geometry import Point
from game_automation.core.ports import InputDevice
from game_automation.core.runner import Sleeper, ScriptRunner
from game_automation.core.script import Script
from game_automation.core.windows import ScreenWindow


RECORDED_CLICK_SCRIPT = Script(
    window=ScreenWindow(),
    actions=(
        Wait(3),
        Click(Point(242, 92)),
        Wait(3),
        Click(Point(736, 323)),
        Wait(10),
        Click(Point(741, 400)),
    ),
)


def build_recorded_click_script() -> Script:
    """构造按已记录坐标顺序点击的脚本。"""
    return RECORDED_CLICK_SCRIPT


def run_recorded_click_script(
    device: InputDevice,
    sleeper: Sleeper = time.sleep,
) -> None:
    """使用指定输入设备运行已记录坐标点击脚本。"""
    ScriptRunner(device=device, sleeper=sleeper).run(build_recorded_click_script())
