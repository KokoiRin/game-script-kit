"""验证图片模板别名的领域和执行行为。"""

import pytest

from game_automation.portable.domain import (
    ImageExists,
    ImageRef,
    ImageTemplate,
    ImageTarget,
    NamedImage,
    TargetCatalog,
    UnknownImageNameError,
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


def test_target_catalog_reports_unknown_image_name() -> None:
    """验证未知图片名称会给出可读错误。"""
    catalog = TargetCatalog()

    with pytest.raises(UnknownImageNameError, match="unknown image target: 开始按钮"):
        catalog.resolve_image(ImageRef("开始按钮"))


def test_image_exists_can_hold_image_ref() -> None:
    """验证图片存在条件可以保留图片引用。"""
    condition = ImageExists(ImageRef("开始按钮"))

    assert condition.template == ImageRef("开始按钮")


def test_image_target_can_hold_image_ref() -> None:
    """验证图片点击目标可以保留图片引用。"""
    target = ImageTarget(ImageRef("开始按钮"))

    assert target.template == ImageRef("开始按钮")
