"""导出项目内置脚本定义和默认脚本注册表。

本 module 只聚合脚本定义和默认 catalog；它不运行脚本、不检查运行端口需求，
也不创建平台 adapter。
"""

from game_automation.portable.scripts_manager.conditional_color_demo import (
    CONDITIONAL_COLOR_DEMO_SCRIPT,
    build_conditional_color_demo_script,
)
from game_automation.portable.scripts_manager.catalog import DEFAULT_SCRIPT_CATALOG
from game_automation.portable.scripts_manager.demo import DEMO_SCRIPT, build_demo_script
from game_automation.portable.scripts_manager.recorded_clicks import (
    RECORDED_CLICKS_SCRIPT,
    build_recorded_clicks_script,
)
from game_automation.portable.scripts_manager.repeat_demo import (
    REPEAT_DEMO_SCRIPT,
    build_repeat_demo_script,
)
from game_automation.portable.scripts_manager.wait_until_color_demo import (
    WAIT_UNTIL_COLOR_DEMO_SCRIPT,
    build_wait_until_color_demo_script,
)

__all__ = [
    "DEFAULT_SCRIPT_CATALOG",
    "DEMO_SCRIPT",
    "CONDITIONAL_COLOR_DEMO_SCRIPT",
    "RECORDED_CLICKS_SCRIPT",
    "REPEAT_DEMO_SCRIPT",
    "WAIT_UNTIL_COLOR_DEMO_SCRIPT",
    "build_conditional_color_demo_script",
    "build_demo_script",
    "build_recorded_clicks_script",
    "build_repeat_demo_script",
    "build_wait_until_color_demo_script",
]
