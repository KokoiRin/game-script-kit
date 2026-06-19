"""验证固定点位别名的领域和执行行为。"""

import pytest

from game_automation.portable.domain import (
    Click,
    NamedPoint,
    OffsetTarget,
    Point,
    PointRef,
    ScreenWindow,
    Script,
    TargetCatalog,
    UnknownPointNameError,
)


def test_named_point_preserves_name_and_point() -> None:
    """验证命名点位会保留稳定名称和固定坐标。"""
    target = NamedPoint("头像", Point(242, 92))

    assert target.name == "头像"
    assert target.point == Point(242, 92)


def test_named_point_rejects_blank_name() -> None:
    """验证命名点位拒绝空白名称。"""
    with pytest.raises(ValueError, match="point name cannot be empty"):
        NamedPoint("  ", Point(1, 2))


def test_target_catalog_resolves_point_ref() -> None:
    """验证资源目录能把点位引用解析为固定坐标。"""
    catalog = TargetCatalog(points=(NamedPoint("头像", Point(242, 92)),))

    assert catalog.resolve_point(PointRef("头像")) == Point(242, 92)


def test_target_catalog_reports_unknown_point_name() -> None:
    """验证未知点位名称会给出可读错误。"""
    catalog = TargetCatalog()

    with pytest.raises(UnknownPointNameError, match="unknown point target: 头像"):
        catalog.resolve_point(PointRef("头像"))


def test_script_uses_empty_target_catalog_by_default() -> None:
    """验证现有脚本构造默认带空资源目录。"""
    script = Script(
        name="default-resources",
        window=ScreenWindow(),
        steps=(Click(Point(1, 2)),),
    )

    assert script.resources == TargetCatalog()


def test_script_can_carry_target_catalog() -> None:
    """验证脚本可以携带命名点位资源目录。"""
    catalog = TargetCatalog(points=(NamedPoint("头像", Point(242, 92)),))
    script = Script(
        name="named-resources",
        window=ScreenWindow(),
        steps=(Click(PointRef("头像")),),
        resources=catalog,
    )

    assert script.resources == catalog


def test_click_can_hold_point_ref_target() -> None:
    """验证点击动作可以保留命名点位引用目标。"""
    action = Click(PointRef("头像"))

    assert action.point == PointRef("头像")


def test_point_offset_returns_new_point() -> None:
    """验证固定点位 offset 返回新点且不修改原点。"""
    point = Point(242, 92)

    shifted = point.offset(x=120, y=-5)

    assert shifted == Point(362, 87)
    assert point == Point(242, 92)


def test_point_ref_offset_builds_offset_target() -> None:
    """验证命名点位引用可以构造偏移目标。"""
    target = PointRef("头像").offset(x=120, y=0)

    assert target == OffsetTarget(PointRef("头像"), Point(120, 0))


def test_click_can_hold_offset_target() -> None:
    """验证点击动作可以保留偏移目标。"""
    target = OffsetTarget(PointRef("头像"), Point(120, 0))

    assert Click(target).point == target
