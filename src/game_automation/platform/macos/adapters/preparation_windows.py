"""实现素材准备的 macOS 窗口查询与按候选激活。

本 module 复用 Accessibility backend 和应用激活能力；不创建 Script、
不调用运行用例，也不把选择状态保存在脚本 catalog 中。
"""

import time
from collections.abc import Callable
from hashlib import sha256

from game_automation.platform.macos.adapters.application_window import (
    MacOSWindowBackend,
    MacOSWindowCandidate,
)
from game_automation.portable.application.ports import ApplicationActivator
from game_automation.portable.preparation.models import DesktopWindow


class MacOSPreparationWindows:
    def __init__(
        self,
        *,
        backend: MacOSWindowBackend | None = None,
        activator: ApplicationActivator | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        """保存可注入的平台依赖，服务构造时不读取窗口或申请权限。"""
        self._backend = backend
        self._activator = activator
        self._sleeper = sleeper

    def _window_backend(self) -> MacOSWindowBackend:
        """在首次窗口请求时加载 Accessibility adapter。"""
        if self._backend is None:
            from game_automation.platform.macos.adapters.accessibility_window_backend import (
                MacOSAccessibilityWindowBackend,
            )

            self._backend = MacOSAccessibilityWindowBackend()
        return self._backend

    def list_windows(self, application: str) -> tuple[DesktopWindow, ...]:
        """列出应用窗口并生成可在下一次请求核对的候选标识。"""
        return tuple(
            _window_value(application, window)
            for window in self._window_backend().list_windows(application)
        )

    def focus_window(self, application: str, window_id: str) -> DesktopWindow:
        """复核候选、激活并 Raise 目标，随后重新读取其范围。"""
        backend = self._window_backend()
        candidates = backend.list_windows(application)
        target = next(
            (window for window in candidates if _window_id(window) == window_id), None
        )
        if target is None:
            raise RuntimeError(
                "selected window changed or closed; refresh the window list"
            )
        if (
            sum(
                window.pid == target.pid and window.title == target.title
                for window in candidates
            )
            > 1
        ):
            raise RuntimeError(
                "multiple windows have the same title; choose a uniquely titled window"
            )
        if self._activator is None:
            from game_automation.platform.macos.adapters.application_activation import (
                MacOSApplicationActivator,
            )

            self._activator = MacOSApplicationActivator()
        self._activator.activate(application)
        backend.raise_window(target)
        self._sleeper(0.2)
        current = next(
            (
                window
                for window in backend.list_windows(application)
                if _window_id(window) == window_id
            ),
            None,
        )
        if current is None:
            raise RuntimeError(
                "selected window changed during activation; refresh the window list"
            )
        return _window_value(application, current)


def _window_id(window: MacOSWindowCandidate) -> str:
    """把进程、临时 AX 序号和标题绑定，避免旧序号指向另一窗口。"""
    title_key = sha256(window.title.encode("utf-8")).hexdigest()[:16]
    return f"{window.pid}:{window.window_number}:{title_key}"


def _window_value(application: str, window: MacOSWindowCandidate) -> DesktopWindow:
    """将平台窗口转换成准备服务的稳定值对象。"""
    return DesktopWindow(_window_id(window), application, window.title, window.rect)
