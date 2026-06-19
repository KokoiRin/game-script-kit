"""验证桌面屏幕图像定位 adapter 行为。"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from game_automation.platform.desktop.adapters import PyAutoGuiScreenImageLocator
from game_automation.portable.domain import ImageMatch, ImageTemplate, Rect


@dataclass(frozen=True, slots=True)
class FakeBox:
    left: int
    top: int
    width: int
    height: int


class FakeBackend:
    def __init__(self, result) -> None:
        """初始化可记录调用参数的 fake pyautogui backend。"""
        self.result = result
        self.calls = []

    def locateOnScreen(self, image_path, **kwargs):
        """记录模板路径和定位参数，并返回预设结果。"""
        self.calls.append((image_path, kwargs))
        return self.result


class ConfidenceRejectingBackend:
    def locateOnScreen(self, image_path, **kwargs):
        """模拟后端未安装置信度匹配依赖时的 TypeError。"""
        if "confidence" in kwargs:
            raise TypeError("confidence requires OpenCV")
        return FakeBox(1, 2, 3, 4)


class FailingBackend:
    def locateOnScreen(self, image_path, **kwargs):
        """模拟截图或模板读取失败。"""
        raise RuntimeError("screen blocked")


class ImageNotFoundBackend:
    class ImageNotFoundException(Exception):
        """模拟 pyautogui 的未找到异常类型。"""

    def locateOnScreen(self, image_path, **kwargs):
        """模拟后端用异常表示未找到模板。"""
        raise self.ImageNotFoundException("not found")


def test_screen_image_locator_returns_match_from_backend_box() -> None:
    """验证后端 Box 会转换为 ImageMatch。"""
    backend = FakeBackend(FakeBox(left=10, top=20, width=30, height=40))

    match = PyAutoGuiScreenImageLocator(backend=backend).locate(
        ImageTemplate("assets/start.png")
    )

    assert match == ImageMatch(Rect(left=10, top=20, width=30, height=40), confidence=1.0)
    assert backend.calls == [("assets/start.png", {})]


def test_screen_image_locator_passes_region_to_backend() -> None:
    """验证指定搜索区域会传给后端。"""
    backend = FakeBackend(FakeBox(left=10, top=20, width=30, height=40))

    PyAutoGuiScreenImageLocator(backend=backend).locate(
        ImageTemplate("assets/start.png"),
        region=Rect(left=1, top=2, width=300, height=400),
    )

    assert backend.calls == [
        ("assets/start.png", {"region": (1, 2, 300, 400)}),
    ]


def test_screen_image_locator_returns_none_when_backend_returns_none() -> None:
    """验证后端返回 None 时 adapter 表示未找到。"""
    backend = FakeBackend(None)

    assert PyAutoGuiScreenImageLocator(backend=backend).locate(ImageTemplate("x.png")) is None


def test_screen_image_locator_returns_none_for_backend_not_found_exception() -> None:
    """验证后端未找到异常会转换为 None。"""
    assert PyAutoGuiScreenImageLocator(backend=ImageNotFoundBackend()).locate(
        ImageTemplate("x.png")
    ) is None


def test_screen_image_locator_wraps_backend_errors() -> None:
    """验证截图或模板读取错误会包装为清晰 setup 错误。"""
    with pytest.raises(RuntimeError, match="screen image matching"):
        PyAutoGuiScreenImageLocator(backend=FailingBackend()).locate(ImageTemplate("x.png"))


def test_screen_image_locator_reports_unsupported_confidence_matching() -> None:
    """验证后端不支持置信度匹配时报告清晰错误。"""
    with pytest.raises(RuntimeError, match="confidence"):
        PyAutoGuiScreenImageLocator(backend=ConfidenceRejectingBackend()).locate(
            ImageTemplate("x.png"),
            min_confidence=0.8,
        )


@pytest.mark.parametrize("min_confidence", [0.0, -0.1, 1.1])
def test_screen_image_locator_rejects_invalid_min_confidence(min_confidence: float) -> None:
    """验证最低匹配置信度必须在有效范围内。"""
    with pytest.raises(ValueError, match="minimum image match confidence"):
        PyAutoGuiScreenImageLocator(backend=FakeBackend(None)).locate(
            ImageTemplate("x.png"),
            min_confidence=min_confidence,
        )
