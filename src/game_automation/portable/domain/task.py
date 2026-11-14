"""定义直接执行 Python 函数的任务输入及声明依赖。

本模块保存经过发现阶段校验的源码快照和资源声明，不导入或执行任务。
应用层负责发现与运行，执行层通过同一次运行上下文提供动作能力。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from game_automation.portable.domain.point_aliases import TargetCatalog
from game_automation.portable.domain.windows import ScreenWindow, Window


@dataclass(frozen=True, slots=True)
class ScriptTarget:
    """声明一次运行绑定的应用、窗口、逻辑尺寸及输入后端。"""

    application: str
    window_title: str
    width: int
    height: int
    backend: str = "desktop"

    def __post_init__(self) -> None:
        """校验目标身份、固定布局尺寸和显式支持的后端。"""
        if self.backend != "desktop" and not self.uses_native_window:
            raise ValueError(
                "target backend must be desktop, macos-window or macos-window-background"
            )
        if any(
            not isinstance(value, str) or not value.strip()
            for value in (self.application, self.window_title)
        ):
            raise ValueError("script target requires application and window_title")
        if any(
            type(value) is not int or value <= 0 for value in (self.width, self.height)
        ):
            raise ValueError("script target width and height must be positive integers")

    @property
    def uses_native_window(self) -> bool:
        """识别使用独立固定窗口会话的原生输入后端。"""
        return self.backend in ("macos-window", "macos-window-background")


@dataclass(frozen=True, slots=True)
class TaskRequirements:
    """保存本地资源及共享资源引用，供详情检查和端口装配使用。"""

    points: tuple[str, ...] = ()
    images: tuple[str, ...] = ()
    searches: tuple[str, ...] = ()
    states: tuple[str, ...] = ()
    colors: bool = False

    def __post_init__(self) -> None:
        """拒绝无效依赖名称及非布尔能力声明。"""
        for names in (self.points, self.images, self.searches, self.states):
            if not isinstance(names, tuple) or any(
                not isinstance(name, str) or not name.strip() for name in names
            ):
                raise ValueError("task dependencies must be tuples of non-empty names")
        if type(self.colors) is not bool:
            raise ValueError("task colors requirement must be boolean")


@dataclass(frozen=True, slots=True)
class FunctionTask:
    """将固定源码快照与本次任务所需的不可变元信息绑定。"""

    name: str
    source_path: Path
    source: str
    window: Window = field(default_factory=ScreenWindow)
    resources: TargetCatalog = field(default_factory=TargetCatalog)
    target: ScriptTarget | None = None
    requires: TaskRequirements = field(default_factory=TaskRequirements)

    def __post_init__(self) -> None:
        """确保函数任务具有可展示的名称及可执行的源码输入。"""
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("task name cannot be empty")
        if not self.source.strip():
            raise ValueError("task source cannot be empty")
