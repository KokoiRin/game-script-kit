"""提供已记录点击脚本的兼容入口，实际定义位于 scripts 包。"""

from __future__ import annotations

import time

from game_automation.core.ports import InputDevice
from game_automation.core.runner import Sleeper, ScriptRunner
from game_automation.domain import Script
from game_automation.scripts.recorded_clicks import build_recorded_clicks_script


def build_recorded_click_script() -> Script:
    """返回已记录点击命名脚本，保留旧 core API。"""
    return build_recorded_clicks_script()


def run_recorded_click_script(
    device: InputDevice,
    sleeper: Sleeper = time.sleep,
) -> None:
    """使用指定输入设备运行已记录坐标点击脚本。"""
    ScriptRunner(device=device, sleeper=sleeper).run(build_recorded_click_script())
