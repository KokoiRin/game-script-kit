"""提供 demo workflow 的兼容入口，实际脚本定义位于 scripts 包。"""

from __future__ import annotations

import time

from game_automation.core.ports import InputDevice
from game_automation.core.runner import Sleeper, ScriptRunner
from game_automation.core.script import Script
from game_automation.scripts.demo import build_demo_script as build_named_demo_script


def build_demo_script() -> Script:
    """返回 demo 命名脚本，保留旧 core API。"""
    return build_named_demo_script()


def run_demo_workflow(device: InputDevice, sleeper: Sleeper = time.sleep) -> None:
    """运行基于脚本模型的 demo workflow。"""
    ScriptRunner(device=device, sleeper=sleeper).run(build_demo_script())
