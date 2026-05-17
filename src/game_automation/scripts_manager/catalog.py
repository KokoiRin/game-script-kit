"""管理可通过名称查找和启动的脚本集合，以及默认注册表组装。"""

from __future__ import annotations

from collections.abc import Iterable

from game_automation.domain import Script
from game_automation.scripts_manager.demo import build_demo_script
from game_automation.scripts_manager.recorded_clicks import build_recorded_clicks_script


class ScriptNotFoundError(LookupError):
    """表示请求的脚本名称没有注册。"""


class ScriptCatalog:
    def __init__(self, scripts: Iterable[Script]) -> None:
        self._scripts = tuple(scripts)
        self._by_name: dict[str, Script] = {}
        for script in self._scripts:
            if script.name in self._by_name:
                raise ValueError(f"duplicate script name: {script.name}")
            self._by_name[script.name] = script

    def list_names(self) -> tuple[str, ...]:
        return tuple(self._by_name)

    def get(self, name: str) -> Script:
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise ScriptNotFoundError(f"unknown script: {name}") from exc


DEFAULT_SCRIPT_CATALOG = ScriptCatalog(
    (
        build_demo_script(),
        build_recorded_clicks_script(),
    )
)
