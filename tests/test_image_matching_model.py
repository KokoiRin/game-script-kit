"""验证屏幕图像匹配领域模型。"""

from __future__ import annotations

import pytest

from game_automation.portable.domain import ImageLookupResult, ImageMatch, ImageTemplate, Point, Rect


def test_image_template_preserves_path() -> None:
    """验证图像模板会保留模板图片路径。"""
    template = ImageTemplate("assets/start-button.png")

    assert template.path == "assets/start-button.png"


def test_image_template_rejects_empty_path() -> None:
    """验证图像模板拒绝空路径。"""
    with pytest.raises(ValueError, match="image template path cannot be empty"):
        ImageTemplate("")

    with pytest.raises(ValueError, match="image template path cannot be empty"):
        ImageTemplate("   ")


def test_image_match_preserves_rect_confidence_and_center() -> None:
    """验证图像匹配结果会保留区域、置信度并计算中心点。"""
    match = ImageMatch(rect=Rect(left=10, top=20, width=30, height=40), confidence=0.75)

    assert match.rect == Rect(left=10, top=20, width=30, height=40)
    assert match.confidence == 0.75
    assert match.center == Point(x=25, y=40)


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_image_match_rejects_confidence_outside_unit_range(confidence: float) -> None:
    """验证图像匹配结果拒绝 0 到 1 之外的置信度。"""
    with pytest.raises(ValueError, match="image match confidence"):
        ImageMatch(rect=Rect(left=0, top=0, width=10, height=10), confidence=confidence)


def test_image_lookup_result_exposes_match_details_when_found() -> None:
    """验证图片查询成功结果会暴露匹配细节。"""
    match = ImageMatch(rect=Rect(left=10, top=20, width=30, height=40), confidence=0.75)
    result = ImageLookupResult(match)

    assert result.found is True
    assert result.match == match
    assert result.rect == Rect(left=10, top=20, width=30, height=40)
    assert result.center == Point(x=25, y=40)
    assert result.confidence == 0.75


def test_image_lookup_result_exposes_missing_state() -> None:
    """验证图片查询未找到结果不会伪造匹配细节。"""
    result = ImageLookupResult(None)

    assert result.found is False
    assert result.match is None
    assert result.rect is None
    assert result.center is None
    assert result.confidence is None
