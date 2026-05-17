"""管理可通过名称查找和启动的脚本集合。"""

from __future__ import annotations

from collections.abc import Iterable

from game_automation.core.script import Script


class ScriptNotFoundError(LookupError):
    """表示请求的脚本名称没有注册。"""


class ScriptCatalog:
    def __init__(self, scripts: Iterable[Script]) -> None:
        """按注册顺序保存脚本，并建立名称索引。"""
        self._scripts = tuple(scripts)
        self._by_name: dict[str, Script] = {}
        for script in self._scripts:
            # 初始化阶段集中拒绝重复名称，避免运行时目标不明确。
            if script.name in self._by_name:
                raise ValueError(f"duplicate script name: {script.name}")
            self._by_name[script.name] = script

    def list_names(self) -> tuple[str, ...]:
        """按注册顺序返回所有脚本名称。"""
        return tuple(self._by_name)

    def get(self, name: str) -> Script:
        """按名称返回脚本，名称不存在时抛出领域错误。"""
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise ScriptNotFoundError(f"unknown script: {name}") from exc
