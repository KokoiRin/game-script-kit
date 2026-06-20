"""验证图片模板别名的领域和执行行为。"""

import pytest

from game_automation.portable.domain import (
    ImageExists,
    ImageRef,
    ImageSearchSpec,
    ImageTemplate,
    ImageTarget,
    NamedImage,
    NamedImageSearch,
    NamedRegion,
    Rect,
    RegionRef,
    SearchRef,
    TargetCatalog,
    UnknownImageNameError,
    UnknownImageSearchNameError,
    UnknownRegionNameError,
)


def test_named_image_preserves_name_and_template() -> None:
    """验证命名图片会保留稳定名称和图片模板。"""
    image = NamedImage("开始按钮", ImageTemplate("assets/start.png"))

    assert image.name == "开始按钮"
    assert image.template == ImageTemplate("assets/start.png")


def test_named_image_rejects_blank_name() -> None:
    """验证命名图片拒绝空白名称。"""
    with pytest.raises(ValueError, match="image name cannot be empty"):
        NamedImage("", ImageTemplate("assets/start.png"))


def test_target_catalog_resolves_image_ref() -> None:
    """验证资源目录能把图片引用解析为图片模板。"""
    catalog = TargetCatalog(images=(NamedImage("开始按钮", ImageTemplate("assets/start.png")),))

    assert catalog.resolve_image(ImageRef("开始按钮")) == ImageTemplate("assets/start.png")


def test_target_catalog_resolves_region_ref() -> None:
    """验证资源目录能把区域引用解析为搜索区域。"""
    catalog = TargetCatalog(regions=(NamedRegion("右上弹窗", Rect(1800, 120, 700, 500)),))

    assert catalog.resolve_region(RegionRef("右上弹窗")) == Rect(1800, 120, 700, 500)


def test_target_catalog_resolves_image_search_ref() -> None:
    """验证资源目录能解析图片、区域和阈值组成的搜索规格。"""
    catalog = TargetCatalog(
        images=(NamedImage("离开", ImageTemplate("assets/离开.png")),),
        regions=(NamedRegion("右上弹窗", Rect(1800, 120, 700, 500)),),
        searches=(
            NamedImageSearch(
                "离开按钮",
                ImageSearchSpec(
                    ImageRef("离开"),
                    region=RegionRef("右上弹窗"),
                    min_confidence=0.8,
                ),
            ),
        ),
    )

    assert catalog.resolve_search(SearchRef("离开按钮")) == ImageSearchSpec(
        ImageTemplate("assets/离开.png"),
        region=Rect(1800, 120, 700, 500),
        min_confidence=0.8,
    )


def test_target_catalog_reports_unknown_image_name() -> None:
    """验证未知图片名称会给出可读错误。"""
    catalog = TargetCatalog()

    with pytest.raises(UnknownImageNameError, match="unknown image target: 开始按钮"):
        catalog.resolve_image(ImageRef("开始按钮"))


def test_target_catalog_reports_unknown_region_name() -> None:
    """验证未知区域名称会给出可读错误。"""
    catalog = TargetCatalog()

    with pytest.raises(UnknownRegionNameError, match="unknown region target: 右上弹窗"):
        catalog.resolve_region(RegionRef("右上弹窗"))


def test_target_catalog_reports_unknown_image_search_name() -> None:
    """验证未知图片搜索名称会给出可读错误。"""
    catalog = TargetCatalog()

    with pytest.raises(UnknownImageSearchNameError, match="unknown image search target: 离开按钮"):
        catalog.resolve_search(SearchRef("离开按钮"))


def test_image_exists_can_hold_image_ref() -> None:
    """验证图片存在条件可以保留图片引用。"""
    condition = ImageExists(ImageRef("开始按钮"))

    assert condition.template == ImageRef("开始按钮")


def test_image_target_can_hold_image_ref() -> None:
    """验证图片点击目标可以保留图片引用。"""
    target = ImageTarget(ImageRef("开始按钮"))

    assert target.template == ImageRef("开始按钮")
