"""管理可通过名称查找的任务集合。

本 module 只负责任务注册、去重和按名称查找；它不运行任务，
也不承担 CLI 参数解析或 adapter 选择。
"""

from __future__ import annotations

from collections.abc import Iterable

from game_automation.portable.domain.task import FunctionTask


class TaskNotFoundError(LookupError):
    """表示请求的任务名称没有注册。"""


class TaskCatalog:
    def __init__(self, tasks: Iterable[FunctionTask] = ()) -> None:
        """建立函数任务的名称索引并拒绝重名。"""
        self._tasks = tuple(tasks)
        self._by_name: dict[str, FunctionTask] = {}
        for task in self._tasks:
            if task.name in self._by_name:
                raise ValueError(f"duplicate task name: {task.name}")
            self._by_name[task.name] = task

    def list_names(self) -> tuple[str, ...]:
        """按注册顺序返回可供入口展示的任务名称。"""
        return tuple(self._by_name)

    def get(self, name: str) -> FunctionTask:
        """按名称读取任务定义并归一化未找到错误。"""
        try:
            return self._by_name[name]
        except KeyError as exc:
            raise TaskNotFoundError(f"unknown task: {name}") from exc
