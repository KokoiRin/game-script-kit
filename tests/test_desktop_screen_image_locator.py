"""验证桌面屏幕图像定位 adapter 行为。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
import pytest

from game_automation.platform.desktop.adapters import image_matching as image_matching_adapter
from game_automation.platform.desktop.adapters import PyAutoGuiScreenImageLocator
from game_automation.portable.domain import ImageSearchRequest, ImageTemplate, Rect


class ScreenshotBackend:
    def __init__(self, image: Image.Image, pointer_size: tuple[int, int] | None = None) -> None:
        """初始化只提供截图能力的 fake backend。"""
        self.image = image
        self.pointer_size = pointer_size if pointer_size is not None else image.size
        self.screenshot_calls = 0

    def screenshot(self) -> Image.Image:
        """返回测试构造的屏幕截图。"""
        self.screenshot_calls += 1
        return self.image

    def size(self) -> tuple[int, int]:
        """返回 fake 鼠标坐标系尺寸。"""
        return self.pointer_size


class FailingScreenshotBackend:
    def screenshot(self) -> Image.Image:
        """模拟截图权限或平台截图失败。"""
        raise RuntimeError("screen blocked")


class FakeLogger:
    def __init__(self) -> None:
        """初始化日志列表。"""
        self.messages: list[str] = []

    def log(self, message: str) -> None:
        """记录一条日志消息。"""
        self.messages.append(message)


class CountingNumpy:
    def __init__(self, numpy_module) -> None:
        """包装 numpy 模块并记录 array 输入图像尺寸。"""
        self._numpy = numpy_module
        self.array_sizes: list[tuple[int, int]] = []

    def array(self, value):
        """记录 PIL 图像尺寸后委托真实 numpy.array。"""
        if isinstance(value, Image.Image):
            self.array_sizes.append(value.size)
        return self._numpy.array(value)


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


def test_screen_image_locator_logs_stage_durations(tmp_path) -> None:
    """验证 adapter 会记录截图、模板加载和匹配阶段耗时。"""
    template = _build_template_image()
    template_path = tmp_path / "button.png"
    template.save(template_path)
    screenshot = Image.new("RGB", (40, 30), "white")
    screenshot.paste(template, (12, 9))
    logger = FakeLogger()

    PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(screenshot)).locate(
        ImageTemplate(str(template_path)),
        min_confidence=0.8,
        logger=logger,
    )

    assert len(logger.messages) == 1
    message = logger.messages[0]
    assert message.startswith("image match stages ")
    assert f"template={template_path}" in message
    assert "screenshot_size=40x30" in message
    assert "template_size=8x6" in message
    assert "cv_load_ms=" in message
    assert "screenshot_ms=" in message
    assert "template_load_ms=" in message
    assert "match_ms=" in message
    assert "total_ms=" in message
    assert "found=True" in message
    assert "confidence=" in message


def test_screen_image_locator_batch_matches_many_templates_with_one_screenshot(tmp_path) -> None:
    """验证批量定位会复用同一张截图匹配多张模板。"""
    first_template = _build_template_image()
    second_template = _build_second_template_image()
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    first_template.save(first_path)
    second_template.save(second_path)
    screenshot = Image.new("RGB", (80, 50), "white")
    screenshot.paste(first_template, (12, 9))
    screenshot.paste(second_template, (44, 31))
    backend = ScreenshotBackend(screenshot)
    logger = FakeLogger()

    results = PyAutoGuiScreenImageLocator(backend=backend).locate_many(
        (ImageTemplate(str(first_path)), ImageTemplate(str(second_path))),
        min_confidence=0.8,
        logger=logger,
    )

    assert backend.screenshot_calls == 1
    assert [result.template for result in results] == [
        ImageTemplate(str(first_path)),
        ImageTemplate(str(second_path)),
    ]
    assert results[0].match is not None
    assert results[0].match.rect == Rect(left=12, top=9, width=8, height=6)
    assert results[1].match is not None
    assert results[1].match.rect == Rect(left=44, top=31, width=8, height=6)
    assert any("image batch match stages " in message for message in logger.messages)
    assert any("template_count=2" in message for message in logger.messages)


def test_screen_image_locator_batch_matches_requests_with_independent_regions(tmp_path) -> None:
    """验证批量搜索请求可以在同一张截图上使用各自区域。"""
    first_template = _build_template_image()
    second_template = _build_second_template_image()
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    first_template.save(first_path)
    second_template.save(second_path)
    screenshot = Image.new("RGB", (120, 80), "white")
    screenshot.paste(first_template, (20, 10))
    screenshot.paste(second_template, (82, 52))
    backend = ScreenshotBackend(screenshot)

    results = PyAutoGuiScreenImageLocator(backend=backend).locate_requests(
        (
            ImageSearchRequest(
                ImageTemplate(str(first_path)),
                region=Rect(left=10, top=5, width=40, height=30),
                min_confidence=0.8,
            ),
            ImageSearchRequest(
                ImageTemplate(str(second_path)),
                region=Rect(left=70, top=45, width=40, height=30),
                min_confidence=0.8,
            ),
        )
    )

    assert backend.screenshot_calls == 1
    assert results[0].match is not None
    assert results[0].match.rect == Rect(left=20, top=10, width=8, height=6)
    assert results[1].match is not None
    assert results[1].match.rect == Rect(left=82, top=52, width=8, height=6)


def test_screen_image_locator_batch_keeps_best_confidence_when_below_threshold(tmp_path) -> None:
    """验证批量匹配未达阈值时仍保留 OpenCV 最佳分数和位置。"""
    template = _build_template_image()
    template_path = tmp_path / "button.png"
    template.save(template_path)
    screenshot = Image.new("RGB", (40, 30), "white")

    results = PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(screenshot)).locate_requests(
        (
            ImageSearchRequest(
                ImageTemplate(str(template_path)),
                min_confidence=0.99,
            ),
        )
    )

    assert results[0].found is False
    assert results[0].confidence is None
    assert results[0].best_confidence is not None
    assert 0 <= results[0].best_confidence < 0.99
    assert results[0].best_rect is not None


def test_screen_image_locator_batch_converts_screenshot_to_array_once(tmp_path, monkeypatch) -> None:
    """验证批量定位只把同一张截图转换为一次 OpenCV 数组。"""
    cv2, numpy = image_matching_adapter._load_cv_modules()
    counting_numpy = CountingNumpy(numpy)
    monkeypatch.setattr(
        image_matching_adapter,
        "_load_cv_modules",
        lambda: (cv2, counting_numpy),
    )
    first_template = _build_template_image()
    second_template = _build_second_template_image()
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    first_template.save(first_path)
    second_template.save(second_path)
    screenshot = Image.new("RGB", (80, 50), "white")
    screenshot.paste(first_template, (12, 9))
    screenshot.paste(second_template, (44, 31))

    PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(screenshot)).locate_many(
        (ImageTemplate(str(first_path)), ImageTemplate(str(second_path))),
        min_confidence=0.8,
    )

    assert counting_numpy.array_sizes.count((80, 50)) == 1


def test_screen_image_locator_reuses_cached_template_image(tmp_path, monkeypatch) -> None:
    """验证重复使用同一模板时不重复读取模板文件。"""
    template = _build_template_image()
    template_path = tmp_path / "button.png"
    template.save(template_path)
    screenshot = Image.new("RGB", (40, 30), "white")
    screenshot.paste(template, (12, 9))
    open_calls = []
    real_open = image_matching_adapter.Image.open

    def counting_open(path):
        """记录模板文件读取次数，并委托给真实 PIL open。"""
        open_calls.append(Path(path))
        return real_open(path)

    monkeypatch.setattr(image_matching_adapter.Image, "open", counting_open)
    PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(screenshot)).locate(
        ImageTemplate(str(template_path)),
        min_confidence=0.8,
    )
    PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(screenshot)).locate(
        ImageTemplate(str(template_path)),
        min_confidence=0.8,
    )

    assert open_calls == [template_path]


def test_screen_image_locator_batch_stops_after_first_match(tmp_path) -> None:
    """验证批量定位早停后把后续模板标记为 skipped。"""
    first_template = _build_template_image()
    second_template = _build_second_template_image()
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    first_template.save(first_path)
    second_template.save(second_path)
    screenshot = Image.new("RGB", (80, 50), "white")
    screenshot.paste(first_template, (12, 9))
    screenshot.paste(second_template, (44, 31))
    logger = FakeLogger()

    results = PyAutoGuiScreenImageLocator(backend=ScreenshotBackend(screenshot)).locate_many(
        (ImageTemplate(str(first_path)), ImageTemplate(str(second_path))),
        min_confidence=0.8,
        logger=logger,
        stop_on_first_match=True,
    )

    assert results[0].found is True
    assert results[0].skipped is False
    assert results[1].found is False
    assert results[1].skipped is True
    assert any("checked_count=1" in message for message in logger.messages)
    assert any("skipped_count=1" in message for message in logger.messages)


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


def test_screen_image_locator_converts_retina_screenshot_pixels_to_pointer_coordinates(
    tmp_path,
) -> None:
    """验证 Retina 截图像素会折算为鼠标可点击坐标。"""
    template = _build_template_image()
    template_path = tmp_path / "button.png"
    template.save(template_path)
    screenshot = Image.new("RGB", (40, 30), "white")
    screenshot.paste(template, (12, 8))

    match = PyAutoGuiScreenImageLocator(
        backend=ScreenshotBackend(screenshot, pointer_size=(20, 15))
    ).locate(
        ImageTemplate(str(template_path)),
        min_confidence=0.8,
    )

    assert match is not None
    assert match.rect == Rect(left=6, top=4, width=4, height=3)


def test_screen_image_locator_interprets_region_as_pointer_coordinates_on_retina(
    tmp_path,
) -> None:
    """验证 Retina 下搜索区域按鼠标坐标解释后再裁剪截图。"""
    template = _build_template_image()
    template_path = tmp_path / "button.png"
    template.save(template_path)
    screenshot = Image.new("RGB", (80, 60), "white")
    screenshot.paste(template, (24, 12))

    match = PyAutoGuiScreenImageLocator(
        backend=ScreenshotBackend(screenshot, pointer_size=(40, 30))
    ).locate(
        ImageTemplate(str(template_path)),
        region=Rect(left=10, top=5, width=20, height=10),
        min_confidence=0.8,
    )

    assert match is not None
    assert match.rect == Rect(left=12, top=6, width=4, height=3)


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


def _build_second_template_image() -> Image.Image:
    """构造第二张带纹理模板，避免批量匹配测试中两图混淆。"""
    image = Image.new("RGB", (8, 6), "green")
    image.putpixel((2, 2), (255, 255, 0))
    image.putpixel((6, 4), (0, 0, 0))
    return image
