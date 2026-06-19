"""实现本地 UI 截屏诊断所需的桌面截图 adapter。

本 module 只封装 pyautogui 截图和保存文件的副作用；它不解释图像匹配语义，
也不决定 UI 如何展示或命名诊断截图。
"""

from __future__ import annotations

from pathlib import Path


class PyAutoGuiScreenCapture:
    def __init__(self, backend: object | None = None) -> None:
        """初始化桌面截屏 adapter，可注入 backend 便于测试。"""
        self._backend = backend if backend is not None else self._load_backend()

    def capture(self, path: Path) -> None:
        """截取当前屏幕并保存到指定路径。"""
        try:
            image = self._backend.screenshot()
            image.save(path)
        except Exception as exc:
            raise RuntimeError(
                "failed to capture screen screenshot. Check screenshot permissions."
            ) from exc

    def _load_backend(self) -> object:
        """延迟加载 pyautogui，避免普通导入触发平台依赖。"""
        try:
            import pyautogui
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "pyautogui is required for screen capture. "
                "Install dependencies with: pip install -e \".[dev]\""
            ) from exc
        return pyautogui
