"""导出项目内置脚本定义和默认脚本注册表。"""

from game_automation.scripts.catalog import DEFAULT_SCRIPT_CATALOG
from game_automation.scripts.demo import DEMO_SCRIPT, build_demo_script
from game_automation.scripts.recorded_clicks import (
    RECORDED_CLICKS_SCRIPT,
    build_recorded_clicks_script,
)

__all__ = [
    "DEFAULT_SCRIPT_CATALOG",
    "DEMO_SCRIPT",
    "RECORDED_CLICKS_SCRIPT",
    "build_demo_script",
    "build_recorded_clicks_script",
]
