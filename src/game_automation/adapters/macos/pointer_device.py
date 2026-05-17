"""实现 macOS 鼠标指针 adapter，将核心协议转换为 pyautogui 调用。"""

from __future__ import annotations

import platform
from types import ModuleType

from game_automation.core.errors import AdapterSetupError, AdapterUnsupportedError
from game_automation.core.geometry import Point


class MacOSPointerDevice:
    def __init__(self, backend: ModuleType | None = None) -> None:
        """初始化 macOS 鼠标指针 adapter，可注入 backend 以便测试。"""
        if platform.system() != "Darwin" and backend is None:
            # 没有注入测试 backend 时，真实 adapter 只能在 macOS 上运行。
            raise AdapterUnsupportedError("macOS pointer adapter requires Darwin")
        self._backend = backend if backend is not None else self._load_backend()
        self._configure_backend()

    def click(self, target: Point) -> None:
        """把跨平台点击请求转换为 macOS 左键点击。"""
        self._call_backend("click", target.x, target.y, button="left")

    def drag_to(
        self,
        start: Point,
        end: Point,
        duration_seconds: float = 0.0,
    ) -> None:
        """把跨平台拖拽请求转换为 macOS 左键拖拽。"""
        # pyautogui 的 dragTo 以当前位置为起点，所以先显式移动到拖动起点。
        self._move_to(start, duration_seconds=0.0)
        self._call_backend(
            "dragTo",
            end.x,
            end.y,
            duration=duration_seconds,
            button="left",
        )

    def _move_to(self, target: Point, duration_seconds: float = 0.0) -> None:
        """在 adapter 内部移动指针，用于支持拖拽起点定位。"""
        self._call_backend("moveTo", target.x, target.y, duration=duration_seconds)

    def _load_backend(self) -> ModuleType:
        """延迟加载 pyautogui，避免核心逻辑导入时触发平台依赖。"""
        try:
            import pyautogui
        except ModuleNotFoundError as exc:
            raise AdapterSetupError(
                "pyautogui is required for the macOS pointer adapter. "
                "Install dependencies with: pip install -e \".[dev]\""
            ) from exc
        return pyautogui

    def _configure_backend(self) -> None:
        """配置 pyautogui 的安全开关和动作间隔。"""
        try:
            self._backend.FAILSAFE = True
            self._backend.PAUSE = 0.05
        except Exception as exc:  # pragma: no cover - defensive for alternate backends.
            raise AdapterSetupError("failed to configure macOS pointer backend") from exc

    def _call_backend(self, method_name: str, *args: object, **kwargs: object) -> None:
        """调用底层 backend，并把底层异常包装成 adapter 级错误。"""
        method = getattr(self._backend, method_name)
        try:
            method(*args, **kwargs)
        except Exception as exc:
            raise AdapterSetupError(
                "macOS pointer operation failed. Check Accessibility permissions "
                "for the terminal or Python runtime."
            ) from exc
