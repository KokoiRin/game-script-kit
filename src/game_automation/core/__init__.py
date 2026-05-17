"""聚合导出平台无关核心层的公共 API。"""

from game_automation.core.demo_workflow import build_demo_script, run_demo_workflow
from game_automation.core.errors import (
    AdapterSetupError,
    AdapterUnsupportedError,
)
from game_automation.core.ports import InputDevice, KeyStateReader, PointerPositionReader
from game_automation.core.recorded_click_script import (
    build_recorded_click_script,
    run_recorded_click_script,
)
from game_automation.core.runner import ScriptRunner
from game_automation.core.script_catalog import ScriptCatalog, ScriptNotFoundError

__all__ = [
    "AdapterSetupError",
    "AdapterUnsupportedError",
    "InputDevice",
    "KeyStateReader",
    "PointerPositionReader",
    "ScriptCatalog",
    "ScriptNotFoundError",
    "ScriptRunner",
    "build_recorded_click_script",
    "build_demo_script",
    "run_recorded_click_script",
    "run_demo_workflow",
]
