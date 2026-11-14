"""管理可通过名称查找的脚本集合。

本 module 只负责脚本注册、去重和按名称查找；它不运行脚本，
也不承担 CLI 参数解析或 adapter 选择。
"""

from __future__ import annotations

from collections.abc import Iterable

from game_automation.portable.domain.task import FunctionTask


class ScriptNotFoundError(LookupError):
    """表示请求的脚本名称没有注册。"""


class ScriptCatalog:
    def __init__(self, scripts: Iterable[FunctionTask] = ()) -> None:
        """建立函数任务的名称索引并拒绝重名。"""
        self._scripts = tuple(scripts)
        self._by_name: dict[str, FunctionTask] = {}
        for script in self._scripts:
            if script.name in self._by_name:
                raise ValueError(f"duplicate script name: {script.name}")
            self._by_name[script.name] = script

    def list_names(self) -> tuple[str, ...]:
        """按注册顺序返回可供入口展示的任务名称。"""
        return tuple(self._by_name)

    def get(self, name: str) -> FunctionTask:
        """按名称读取任务定义并归一化未找到错误。"""
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise ScriptNotFoundError(f"unknown script: {name}") from exc
