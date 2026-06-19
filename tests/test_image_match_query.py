"""验证图片匹配查询会解析资源并返回可观察结果。"""

import pytest

from game_automation.portable.domain import (
    ImageRef,
    ImageMatch,
    ImageTemplate,
    NamedImage,
    Rect,
    TargetCatalog,
)
from game_automation.portable.engine.image_query import locate_image


class FakeImageLocator:
    """提供查询测试用固定图像匹配结果。"""

    def __init__(self, match: ImageMatch | None) -> None:
        """保存固定匹配结果并记录定位请求。"""
        self.match = match
        self.calls = []

    def locate(
        self,
        template: ImageTemplate,
        *,
        region: Rect | None = None,
        min_confidence: float = 1.0,
    ) -> ImageMatch | None:
        """记录定位参数并返回固定匹配结果。"""
        self.calls.append((template, region, min_confidence))
        return self.match


def test_locate_image_with_direct_template_returns_found_result() -> None:
    """验证直接模板查询会返回 found 结果。"""
    match = ImageMatch(Rect(10, 20, 30, 40), confidence=0.9)
    locator = FakeImageLocator(match)

    result = locate_image(
        ImageTemplate("assets/start.png"),
        image_locator=locator,
        resources=TargetCatalog(),
        region=Rect(1, 2, 30, 40),
        min_confidence=0.8,
    )

    assert result.found is True
    assert result.match == match
    assert locator.calls == [
        (ImageTemplate("assets/start.png"), Rect(1, 2, 30, 40), 0.8)
    ]


def test_locate_image_resolves_named_image_before_calling_locator() -> None:
    """验证命名图片查询会先解析为模板。"""
    locator = FakeImageLocator(ImageMatch(Rect(10, 20, 30, 40), confidence=0.9))
    resources = TargetCatalog(images=(NamedImage("开始按钮", ImageTemplate("assets/start.png")),))

    locate_image(
        ImageRef("开始按钮"),
        image_locator=locator,
        resources=resources,
    )

    assert locator.calls == [(ImageTemplate("assets/start.png"), None, 1.0)]


def test_locate_image_returns_missing_result_when_locator_returns_none() -> None:
    """验证未找到图片时查询结果为 found false。"""
    result = locate_image(
        ImageTemplate("assets/missing.png"),
        image_locator=FakeImageLocator(None),
        resources=TargetCatalog(),
    )

    assert result.found is False
    assert result.match is None


def test_locate_image_requires_locator() -> None:
    """验证缺少图像定位端口时报告 setup 错误。"""
    with pytest.raises(RuntimeError, match="image locator"):
        locate_image(
            ImageTemplate("assets/start.png"),
            image_locator=None,
            resources=TargetCatalog(),
        )
