"""实现 engine.ports.PointerPositionReader，通过 pyautogui 读取鼠标屏幕坐标。

本 module 只封装当前指针位置读取；它不记录点、不读取颜色，
也不参与脚本运行。
"""

from __future__ import annotations

from types import ModuleType

from game_automation.portable.domain import Point
from game_automation.portable.engine.ports import PointerPositionReader


class PyAutoGuiPointerPositionReader(PointerPositionReader):
    def __init__(self, backend: ModuleType | None = None) -> None:
        """初始化鼠标坐标读取 adapter，可注入 backend 便于测试。"""
        self._backend = backend if backend is not None else self._load_backend()

    def current_position(self) -> Point:
        """按 PyAutoGUI 二元坐标契约解包结果，将两个分量转为整数领域点。"""
        try:
            position = self._backend.position()
        except Exception as exc:
            raise RuntimeError(
                "failed to read pointer position. Check desktop automation permissions."
            ) from exc

        x, y = position
        return Point(int(x), int(y))

    def _load_backend(self) -> ModuleType:
        """延迟加载 pyautogui，避免导入工具模块时触发平台依赖。"""
        try:
            import pyautogui
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "pyautogui is required for coordinate recording. "
                'Install dependencies with: pip install -e ".[dev]"'
            ) from exc
        return pyautogui
