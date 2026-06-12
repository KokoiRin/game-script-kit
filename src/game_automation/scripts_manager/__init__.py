"""导出项目内置脚本定义和默认脚本注册表。"""

from game_automation.scripts_manager.conditional_color_demo import (
    CONDITIONAL_COLOR_DEMO_SCRIPT,
    build_conditional_color_demo_script,
)
from game_automation.scripts_manager.catalog import DEFAULT_SCRIPT_CATALOG
from game_automation.scripts_manager.demo import DEMO_SCRIPT, build_demo_script
from game_automation.scripts_manager.recorded_clicks import (
    RECORDED_CLICKS_SCRIPT,
    build_recorded_clicks_script,
)
from game_automation.scripts_manager.repeat_demo import (
    REPEAT_DEMO_SCRIPT,
    build_repeat_demo_script,
)

__all__ = [
    "DEFAULT_SCRIPT_CATALOG",
    "DEMO_SCRIPT",
    "CONDITIONAL_COLOR_DEMO_SCRIPT",
    "RECORDED_CLICKS_SCRIPT",
    "REPEAT_DEMO_SCRIPT",
    "build_conditional_color_demo_script",
    "build_demo_script",
    "build_recorded_clicks_script",
    "build_repeat_demo_script",
]
