"""验证公开多点请求、窗口规则和证据，不接触真实桌面或游戏资产。"""

import json
from dataclasses import replace

import pytest
from PIL import Image

from game_automation.platform.desktop.adapters import image_matching as adapter
from game_automation.portable.application.window_state_rules import (
    list_window_state_rules,
    load_window_state_rules,
)
from game_automation.portable.domain import (
    ImageBatchMatchResult,
    ImageMatch,
    ImageSearchRequest,
    ImageTemplate,
    Rect,
    ScreenStateCandidate,
    ScreenStateCandidateResult,
)
from game_automation.portable.domain.color_pattern import ColorPattern, ColorPoint
from tests.test_desktop_screen_image_locator import ScreenshotBackend


def pattern(radius=1):
    """给出分离位置与颜色的固定特征。"""
    return ColorPattern(
        (ColorPoint(4, 6, (100, 120, 140), 5), ColorPoint(12, 14, (180, 60, 30), 5)),
        radius,
    )


def frame(offsets=((0, 0), (0, 0)), errors=(0, 0)):
    """构造独立偏移或通道误差的画面。"""
    image = Image.new("RGB", (40, 40), "black")
    for p, (dx, dy), error in zip(pattern().points, offsets, errors, strict=True):
        image.putpixel((p.x + dx, p.y + dy), (p.rgb[0], p.rgb[1], p.rgb[2] + error))
    return image


def locate(image, value=None, **kwargs):
    """从不存在PNG的公共请求执行固定像素识别。"""
    backend = ScreenshotBackend(image, (20, 20))
    request = ImageSearchRequest(
        ImageTemplate("reference-not-loaded.png"),
        min_confidence=0.1,
        pattern=value or pattern(),
        **kwargs,
    )
    result = adapter.PyAutoGuiScreenImageLocator(backend).locate_requests((request,))[0]
    assert backend.screenshot_calls == 1
    return result


@pytest.mark.parametrize("dx,dy", [(0, 0), (-1, -1), (1, 1), (1, 0), (0, -1)])
def test_shared_translation_and_retina_rectangle(dx, dy):
    """整组一像素平移保持命中，位置换算成逻辑坐标。"""
    result = locate(frame(((dx, dy), (dx, dy))))
    assert result.found and result.matched_points == result.point_count == 2
    assert result.match.rect.left == (4 + dx) // 2
    assert result.match.rect.top == (6 + dy) // 2


def test_independent_offsets_and_distant_pattern_are_not_matches():
    """不允许每个点单独移动，也不扫描其他位置的相同图案。"""
    for offsets in [((1, 0), (-1, 0)), ((8, 8), (8, 8))]:
        result = locate(frame(offsets))
        assert not result.found and result.matched_points < 2


@pytest.mark.parametrize(
    "error,found", [(5, True), (-5, True), (6, False), (-6, False)]
)
def test_all_channels_tolerance_boundary_and_no_partial_threshold(error, found):
    """每个通道都受容差约束，低置信度阈值不能允许缺点。"""
    result = locate(frame(errors=(0, error)), pattern(0))
    assert result.found == found
    assert result.matched_points == (2 if found else 1)


def test_points_only_do_not_load_cv_convert_rgb_or_lower_templates(monkeypatch):
    """纯多点及截断后的模板不触发数组库、整图转换或文件读取。"""

    def forbidden(*args, **kwargs):
        """使无关的图像转换或依赖加载明确失败。"""
        raise AssertionError("points must not load CV or convert RGB")

    monkeypatch.setattr(adapter, "_load_cv_modules", forbidden)
    monkeypatch.setattr(Image.Image, "convert", forbidden)
    backend = ScreenshotBackend(frame())
    requests = (
        ImageSearchRequest(ImageTemplate("missing-low.png"), priority=0),
        ImageSearchRequest(
            ImageTemplate("missing-high.png"), priority=100, pattern=pattern()
        ),
        ImageSearchRequest(ImageTemplate("peer.png"), priority=100, pattern=pattern()),
    )
    result = adapter.PyAutoGuiScreenImageLocator(backend).locate_requests(
        requests, stop_on_priority_match=True
    )
    assert backend.screenshot_calls == 1
    assert result[0].skipped and all(r.found for r in result[1:])


def test_mixed_miss_and_template_hit_share_one_frame(tmp_path):
    """高层多点未命中时仍在同帧下探模板，不重复截图。"""
    import numpy as np

    image = Image.fromarray(
        np.random.default_rng(7).integers(0, 255, (40, 40, 3), dtype=np.uint8)
    )
    path = tmp_path / "template.png"
    image.crop((20, 20, 28, 28)).save(path)
    backend = ScreenshotBackend(image)
    results = adapter.PyAutoGuiScreenImageLocator(backend).locate_requests(
        (
            ImageSearchRequest(
                ImageTemplate("not-read.png"), priority=100, pattern=pattern(0)
            ),
            ImageSearchRequest(
                ImageTemplate(str(path)), priority=0, min_confidence=0.95
            ),
        ),
        stop_on_priority_match=True,
    )
    assert backend.screenshot_calls == 1 and not results[0].found and results[1].found


@pytest.mark.parametrize(
    "kwargs",
    [
        {"x": True},
        {"x": -1},
        {"y": 1.2},
        {"rgb": (0, True, 0)},
        {"rgb": (256, 0, 0)},
        {"tolerance": True},
        {"tolerance": 101},
    ],
)
def test_color_point_rejects_bad_values(kwargs):
    """配置数字必须严格合法，不把布尔和小数转换成坐标颜色。"""
    with pytest.raises(ValueError):
        replace(pattern().points[0], **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"points": ()},
        {"points": (pattern().points[0],) * 2},
        {"offset_radius": True},
        {"offset_radius": 3},
    ],
)
def test_color_pattern_rejects_bad_groups(kwargs):
    """空组、重复点和无界偏移不构成合法特征。"""
    with pytest.raises(ValueError):
        replace(pattern(), **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"point_count": None, "matched_points": 1},
        {"point_count": True, "matched_points": 0},
        {"point_count": 2, "matched_points": True},
        {"point_count": 2, "matched_points": 3},
        {"point_count": 2, "matched_points": 2},
        {
            "point_count": 2,
            "matched_points": 0,
            "match": ImageMatch(Rect(0, 0, 2, 2), 1),
        },
        {"point_count": 2, "matched_points": 1, "skipped": True},
    ],
)
def test_both_public_result_types_reject_inconsistent_counts(kwargs):
    """批量结果和状态结果都不能携带自相矛盾的点数证据。"""
    template = ImageTemplate("ref.png")
    for cls, first in [
        (ImageBatchMatchResult, template),
        (ScreenStateCandidateResult, ScreenStateCandidate("页", template)),
    ]:
        with pytest.raises(ValueError):
            cls(first, **({"match": None, "elapsed_ms": 0} | kwargs))


def config(tmp_path, search_extra=None):
    """建立含参考PNG的公开窗口配置。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    Image.new("RGB", (2, 2)).save(assets / "ref.png")
    search = {
        "image": "ref.png",
        "name": "标题",
        "method": "points",
        "offset_radius": 1,
        "points": [
            {"x": p.x, "y": p.y, "rgb": list(p.rgb), "tolerance": p.tolerance}
            for p in pattern().points
        ],
    }
    search.update(search_extra or {})
    data = {
        "window_size": {"width": 20, "height": 20},
        "pixel_size": {"width": 40, "height": 40},
        "groups": [{"state": "页", "priority": 100, "searches": [search]}],
    }
    (assets / "window-states.json").write_text(json.dumps(data))
    return data


@pytest.mark.parametrize(
    "extra",
    [
        {"method": "unknown"},
        {"method": "template"},
        {"points": None},
        {"points": []},
        {
            "points": [
                {"x": 40, "y": 2, "rgb": [1, 2, 3]},
                {"x": 3, "y": 4, "rgb": [1, 2, 3]},
            ]
        },
        {
            "points": [
                {"x": True, "y": 2, "rgb": [1, 2, 3]},
                {"x": 3, "y": 4, "rgb": [1, 2, 3]},
            ]
        },
        {"points": [{"x": 1, "y": 2, "rgb": [1, 2, 3]}] * 2},
        {"offset_radius": True},
    ],
)
def test_config_rejects_invalid_points_without_falling_back(tmp_path, extra):
    """坏点位配置明确失败，不静默退回模板识别。"""
    config(tmp_path, extra)
    with pytest.raises(ValueError):
        load_window_state_rules(tmp_path)


def test_public_probe_and_wire_preserve_point_counts_and_timing(tmp_path):
    """窗口探测和控制台协议保留实际多点计数及同次源证据。"""
    from game_automation.platform.local_desktop.entrypoints.desktop_backend import (
        observation_wire,
    )
    from game_automation.platform.macos.adapters.window_state_probe import (
        MacOSWindowStateProbe,
    )
    from game_automation.portable.application.state_observation import (
        ObservationPhase,
        ObservationSample,
        ObservationSnapshot,
    )
    from game_automation.portable.domain.screen_state import FrameProof
    from game_automation.portable.preparation.models import DesktopWindow

    config(tmp_path)
    rules = load_window_state_rules(tmp_path)
    listing = list_window_state_rules(tmp_path)["rules"][0]
    assert (
        listing["method"] == "points"
        and listing["point_count"] == 2
        and listing["offset_radius"] == 1
    )
    source = ScreenshotBackend(frame(), (20, 20))
    source.proof = FrameProof(1, 10)
    source.close = lambda: None
    probe = MacOSWindowStateProbe(
        DesktopWindow("1:1", "Test", "页", Rect(0, 0, 20, 20)), rules, source=source
    )
    result = probe.read()
    assert result.current_state == "页" and result.proof == source.proof
    assert result.timing.screenshot_ms + result.timing.recognition_ms == pytest.approx(
        result.elapsed_ms
    )
    wire = observation_wire(
        ObservationSnapshot(
            phase=ObservationPhase.OBSERVING,
            sample=ObservationSample(1, 2, 3, result, 5),
        )
    )
    assert wire["evidence"][0]["method"] == "points"
    assert (
        wire["evidence"][0]["matched_points"] == wire["evidence"][0]["point_count"] == 2
    )


def test_request_rejects_wrong_pattern_type():
    """请求不能用松散字典或字符串冒充已验证的颜色特征。"""
    with pytest.raises(ValueError):
        ImageSearchRequest(ImageTemplate("ref.png"), pattern="bad")
