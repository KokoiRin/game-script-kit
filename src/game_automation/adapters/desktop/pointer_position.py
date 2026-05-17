"""实现桌面鼠标坐标读取 adapter。"""

from __future__ import annotations

from types import ModuleType

from game_automation.core import AdapterSetupError, Point


class PyAutoGuiPointerPositionReader:
    def __init__(self, backend: ModuleType | None = None) -> None:
        """初始化鼠标坐标读取 adapter，可注入 backend 便于测试。"""
        self._backend = backend if backend is not None else self._load_backend()

    def current_position(self) -> Point:
        """读取 pyautogui 当前鼠标坐标并转换为 Point。"""
        try:
            position = self._backend.position()
        except Exception as exc:
            raise AdapterSetupError(
                "failed to read pointer position. Check desktop automation permissions."
            ) from exc

        # pyautogui 可能返回 Point-like 对象，也可能在测试中返回 tuple。
        if hasattr(position, "x") and hasattr(position, "y"):
            x = position.x
            y = position.y
        else:
            x = position[0]
            y = position[1]
        return Point(int(x), int(y))

    def _load_backend(self) -> ModuleType:
        """延迟加载 pyautogui，避免导入工具模块时触发平台依赖。"""
        try:
            import pyautogui
        except ModuleNotFoundError as exc:
            raise AdapterSetupError(
                "pyautogui is required for coordinate recording. "
                "Install dependencies with: pip install -e \".[dev]\""
            ) from exc
        return pyautogui
