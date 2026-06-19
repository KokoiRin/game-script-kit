"""验证桌面截屏诊断 adapter 行为。"""

from __future__ import annotations

import pytest

from game_automation.platform.desktop.adapters import PyAutoGuiScreenCapture


class FakeImage:
    def __init__(self) -> None:
        """初始化 fake 图片并记录保存路径。"""
        self.saved_paths = []

    def save(self, path) -> None:
        """记录 adapter 要写入的截图文件路径。"""
        self.saved_paths.append(path)


class FakeBackend:
    def __init__(self, image: FakeImage) -> None:
        """初始化可返回指定图片的 fake pyautogui backend。"""
        self.image = image
        self.calls = 0

    def screenshot(self) -> FakeImage:
        """模拟 pyautogui.screenshot。"""
        self.calls += 1
        return self.image


class FailingBackend:
    def screenshot(self):
        """模拟截图权限或后端失败。"""
        raise RuntimeError("screen blocked")


def test_screen_capture_saves_backend_screenshot(tmp_path) -> None:
    """验证 adapter 会把 pyautogui 截图保存到指定文件。"""
    image = FakeImage()
    backend = FakeBackend(image)
    path = tmp_path / "latest-screen.png"

    PyAutoGuiScreenCapture(backend=backend).capture(path)

    assert backend.calls == 1
    assert image.saved_paths == [path]


def test_screen_capture_wraps_backend_errors(tmp_path) -> None:
    """验证截图权限或后端失败会转换为清晰错误。"""
    with pytest.raises(RuntimeError, match="screen screenshot"):
        PyAutoGuiScreenCapture(backend=FailingBackend()).capture(tmp_path / "screen.png")
