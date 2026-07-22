"""选择并 Raise 唯一标题匹配的 macOS 顶层窗口。

本 module 负责窗口候选规则和稳定等待；它不直接调用 macOS framework、
不激活应用、不修改脚本，也不解释图片搜索或坐标语义。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time
from typing import Protocol

from game_automation.portable.application.ports import (
    ApplicationWindowController,
    FocusedApplicationWindow,
)
from game_automation.portable.domain import Rect


Sleeper = Callable[[float], None]


@dataclass(frozen=True, slots=True)
class MacOSWindowCandidate:
    """保存 macOS backend 返回的顶层窗口信息。"""

    pid: int
    window_number: int
    title: str
    rect: Rect


class MacOSWindowBackend(Protocol):
    """隔离 macOS framework 类型，便于控制器行为测试。"""

    def list_windows(self, application: str) -> tuple[MacOSWindowCandidate, ...]:
        """列出指定应用当前可见的具名顶层窗口。"""
        ...

    def raise_window(self, window: MacOSWindowCandidate) -> None:
        """通过平台能力 Raise 指定窗口。"""
        ...


class MacOSApplicationWindowController(ApplicationWindowController):
    """按应用名和标题子串锁定唯一 macOS 顶层窗口。"""

    def __init__(
        self,
        *,
        backend: MacOSWindowBackend | None = None,
        sleeper: Sleeper = time.sleep,
        stabilization_seconds: float = 0.2,
    ) -> None:
        """初始化可注入 backend 和等待函数的窗口控制 adapter。"""
        if stabilization_seconds < 0:
            raise ValueError("window stabilization seconds must be non-negative")
        if backend is None:
            from game_automation.platform.macos.adapters.accessibility_window_backend import (
                MacOSAccessibilityWindowBackend,
            )

            backend = MacOSAccessibilityWindowBackend()
        self._backend = backend
        self._sleeper = sleeper
        self._stabilization_seconds = stabilization_seconds

    def focus_window(
        self,
        application: str,
        title_contains: str,
    ) -> FocusedApplicationWindow:
        """选择并 Raise 唯一标题匹配窗口，随后返回屏幕矩形。"""
        normalized_application = application.strip()
        normalized_title = title_contains.strip()
        if not normalized_application:
            raise ValueError("target application must not be empty")
        if not normalized_title:
            raise ValueError("target window title must not be empty")
        title_key = normalized_title.casefold()
        matches = tuple(
            window
            for window in self._backend.list_windows(normalized_application)
            if title_key in window.title.casefold()
        )
        if not matches:
            raise RuntimeError(
                f"target window containing '{normalized_title}' was not found "
                f"for application '{normalized_application}'"
            )
        if len(matches) > 1:
            raise RuntimeError(
                f"target window title '{normalized_title}' matched multiple windows "
                f"for application '{normalized_application}'; use a more specific title"
            )
        target = matches[0]
        self._backend.raise_window(target)
        if self._stabilization_seconds > 0:
            self._sleeper(self._stabilization_seconds)
        return FocusedApplicationWindow(target.title, target.rect)
