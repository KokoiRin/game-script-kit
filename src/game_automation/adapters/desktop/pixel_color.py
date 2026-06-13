"""实现 engine.ports.PixelColorReader，通过 pyautogui 读取屏幕点颜色。

本 module 只封装屏幕截图和像素读取的桌面 I/O；它不判断颜色条件是否成立，
也不决定何时需要取色。
"""

from __future__ import annotations

from types import ModuleType

from game_automation.domain import Color, Point
from game_automation.engine.ports import PixelColorReader


class PyAutoGuiPixelColorReader(PixelColorReader):
    def __init__(self, backend: ModuleType | None = None) -> None:
        """初始化单点取色 adapter，可注入 backend 便于测试。"""
        self._backend = backend if backend is not None else self._load_backend()

    def read_color(self, point: Point) -> Color:
        """读取指定屏幕坐标的像素颜色并转换为 Color。"""
        try:
            image = self._backend.screenshot()
            pixel = image.getpixel((point.x, point.y))
        except Exception as exc:
            raise RuntimeError(
                "failed to read screen color. Check screenshot permissions."
            ) from exc

        red, green, blue = pixel[:3]
        return Color(int(red), int(green), int(blue))

    def _load_backend(self) -> ModuleType:
        """延迟加载 pyautogui，避免导入工具模块时触发平台依赖。"""
        try:
            import pyautogui
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "pyautogui is required for screen color sampling. "
                "Install dependencies with: pip install -e \".[dev]\""
            ) from exc
        return pyautogui
