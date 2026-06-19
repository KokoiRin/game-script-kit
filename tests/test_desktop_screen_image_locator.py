"""验证桌面屏幕图像定位 adapter 行为。"""

from __future__ import annotations

from PIL import Image
import pytest

from game_automation.platform.desktop.adapters import PyAutoGuiScreenImageLocator
from game_automation.portable.domain import ImageTemplate, Rect


class ScreenshotBackend:
    def __init__(self, image: Image.Image) -> None:
        """初始化只提供截图能力的 fake backend。"""
        self.image = image

    def screenshot(self) -> Image.Image:
        """返回测试构造的屏幕截图。"""
        return self.image


class FailingScreenshotBackend:
    def screenshot(self) -> Image.Image:
        """模拟截图权限或平台截图失败。"""
        raise RuntimeError("screen blocked")


def test_screen_image_locator_matches_template_with_opencv_confidence(tmp_path) -> None:
    """验证 adapter 用 OpenCV 返回实际匹配分数和区域。"""
    template = _build_template_image()
    template_path = tmp_path / "button.png"
    template.save(template_path)
    screenshot = Image.new("RGB", (40, 30), "white")
    screenshot.paste(template, (12, 9))

    match = PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(screenshot)).locate(
        ImageTemplate(str(template_path)),
        min_confidence=0.8,
    )

    assert match is not None
    assert match.rect == Rect(left=12, top=9, width=8, height=6)
    assert match.confidence >= 0.99


def test_screen_image_locator_matches_template_inside_region(tmp_path) -> None:
    """验证指定搜索区域会裁剪截图并返回屏幕绝对坐标。"""
    template = _build_template_image()
    template_path = tmp_path / "button.png"
    template.save(template_path)
    screenshot = Image.new("RGB", (60, 40), "white")
    screenshot.paste(template, (22, 13))

    match = PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(screenshot)).locate(
        ImageTemplate(str(template_path)),
        region=Rect(left=20, top=10, width=20, height=20),
        min_confidence=0.8,
    )

    assert match is not None
    assert match.rect == Rect(left=22, top=13, width=8, height=6)


def test_screen_image_locator_returns_none_when_score_is_below_threshold(tmp_path) -> None:
    """验证最高匹配分数低于阈值时 adapter 表示未找到。"""
    template = _build_template_image()
    template_path = tmp_path / "button.png"
    template.save(template_path)
    screenshot = Image.new("RGB", (40, 30), "white")

    assert (
        PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(screenshot)).locate(
            ImageTemplate(str(template_path)),
            min_confidence=0.99,
        )
        is None
    )


def test_screen_image_locator_returns_none_when_template_is_larger_than_screen(tmp_path) -> None:
    """验证模板大于搜索图时 adapter 表示未找到。"""
    template = _build_template_image()
    template_path = tmp_path / "button.png"
    template.save(template_path)
    screenshot = Image.new("RGB", (4, 4), "white")

    assert (
        PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(screenshot)).locate(
            ImageTemplate(str(template_path)),
            min_confidence=0.8,
        )
        is None
    )


def test_screen_image_locator_wraps_backend_errors() -> None:
    """验证截图或模板读取错误会包装为清晰 setup 错误。"""
    with pytest.raises(RuntimeError, match="screen image matching"):
        PyAutoGuiScreenImageLocator(backend=FailingScreenshotBackend()).locate(
            ImageTemplate("x.png")
        )


@pytest.mark.parametrize("min_confidence", [0.0, -0.1, 1.1])
def test_screen_image_locator_rejects_invalid_min_confidence(min_confidence: float) -> None:
    """验证最低匹配置信度必须在有效范围内。"""
    with pytest.raises(ValueError, match="minimum image match confidence"):
        PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(Image.new("RGB", (1, 1)))).locate(
            ImageTemplate("x.png"),
            min_confidence=min_confidence,
        )


def _build_template_image() -> Image.Image:
    """构造带纹理的测试模板，避免纯色模板导致归一化匹配退化。"""
    image = Image.new("RGB", (8, 6), "red")
    image.putpixel((1, 1), (0, 0, 0))
    image.putpixel((5, 3), (0, 0, 255))
    return image
