"""组装项目内置的默认脚本注册表。"""

from __future__ import annotations

from game_automation.core.script_catalog import ScriptCatalog
from game_automation.scripts.demo import build_demo_script
from game_automation.scripts.recorded_clicks import build_recorded_clicks_script


DEFAULT_SCRIPT_CATALOG = ScriptCatalog(
    (
        build_demo_script(),
        build_recorded_clicks_script(),
    )
)
