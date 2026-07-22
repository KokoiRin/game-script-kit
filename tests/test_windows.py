"""验证脚本窗口的坐标解析规则。"""

from game_automation.portable.domain import AreaWindow, Point, Rect, ScreenWindow


def test_screen_window_returns_point_unchanged() -> None:
    """验证屏幕窗口直接使用屏幕坐标。"""
    point = Point(10, 20)

    assert ScreenWindow().resolve(point) == point


def test_area_window_offsets_point_by_rect_origin() -> None:
    """验证区域窗口会把区域内点偏移到屏幕坐标。"""
    window = AreaWindow(Rect(left=100, top=200, width=800, height=600))

    assert window.resolve(Point(10, 20)) == Point(110, 220)


def test_area_window_does_not_clamp_out_of_bounds_point() -> None:
    """验证区域外点仍按同一偏移规则解析。"""
    window = AreaWindow(Rect(left=100, top=200, width=10, height=10))

    assert window.resolve(Point(20, -5)) == Point(120, 195)


def test_screen_window_preserves_image_search_region() -> None:
    """验证屏幕窗口保持整屏默认和显式屏幕搜索区域。"""
    region = Rect(10, 20, 30, 40)

    assert ScreenWindow().resolve_region(None) is None
    assert ScreenWindow().resolve_region(region) == region


def test_area_window_uses_itself_as_default_image_search_region() -> None:
    """验证区域窗口未收到显式区域时使用自身范围。"""
    rect = Rect(left=100, top=200, width=800, height=600)

    assert AreaWindow(rect).resolve_region(None) == rect


def test_area_window_offsets_explicit_image_search_region() -> None:
    """验证区域窗口把显式搜索区域偏移到屏幕坐标。"""
    window = AreaWindow(Rect(left=100, top=200, width=800, height=600))

    assert window.resolve_region(Rect(10, 20, 30, 40)) == Rect(110, 220, 30, 40)
