"""验证优先级截断的公开结果与真实执行数量，不访问桌面。"""

import pytest
from PIL import Image

from game_automation.platform.desktop.adapters import image_matching as adapter
from game_automation.portable.application.window_state_rules import (
    list_window_state_rules,
    load_window_state_rules,
    save_window_state_rule,
)
from game_automation.portable.domain import (
    ImageMatch,
    ImageSearchRequest,
    ImageTemplate,
    Rect,
)
from tests.test_desktop_screen_image_locator import ScreenshotBackend
from tests.test_window_state_rules import preparation as preparation


def test_priority_group_stops_lower_templates_but_finishes_peers(tmp_path, monkeypatch):
    """高层即使分数较低仍截断低层，同层完成且只截图转全图一次。"""
    import numpy

    paths = []
    for i in (1, 2):
        p = tmp_path / f"{i}.png"
        Image.new("RGB", (4, 4), (i, 0, 0)).save(p)
        paths.append(ImageTemplate(str(p)))
    backend = ScreenshotBackend(Image.new("RGB", (64, 64)))
    calls = []
    arrays = []
    array = numpy.array

    def counting(image, *args, **kwargs):
        """记录全图转换而不混淆模板数组。"""
        arrays.append(getattr(image, "size", None))
        return array(image, *args, **kwargs)

    def match(**kw):
        """提供同层不同分数并记录执行次序。"""
        i = kw["template"].image.getpixel((0, 0))[0]
        calls.append(i)
        m = ImageMatch(Rect(0, 0, 4, 4), 0.92 if i == 1 else 0.99)
        return adapter.LocatedTemplate(m, m.confidence, m.rect)

    monkeypatch.setattr(numpy, "array", counting)
    monkeypatch.setattr(adapter, "_locate_template", match)
    req = (
        ImageSearchRequest(
            ImageTemplate(str(tmp_path / "does-not-exist.png")), priority=0
        ),
        ImageSearchRequest(paths[0], priority=100),
        ImageSearchRequest(paths[1], priority=100),
    )
    result = adapter.PyAutoGuiScreenImageLocator(backend).locate_requests(
        req, stop_on_priority_match=True
    )
    assert backend.screenshot_calls == 1 and arrays.count((64, 64)) == 1
    assert calls == [1, 2] and result[0].skipped and result[0].best_confidence is None
    assert result[1].confidence == 0.92 and result[2].confidence == 0.99


@pytest.mark.parametrize("bad", [True, 1.5, "100", None])
def test_request_priority_is_strict_integer(bad):
    """布尔与隐式转换的优先级在领域边界拒绝。"""
    with pytest.raises(ValueError):
        ImageSearchRequest(ImageTemplate("a"), priority=bad)


def test_rule_default_priority_and_preserving_save(tmp_path, preparation):
    """旧规则默认零，同状态追加素材保留已配置优先级。"""
    service, frame = preparation

    def save(name, **kw):
        """复用公开素材登记入口。"""
        return save_window_state_rule(
            tmp_path,
            service,
            frame_id=frame.id,
            crop=Rect(0, 0, 5, 5),
            name=name,
            state="页面",
            **kw,
        )

    save("one", priority=100)
    save("two")
    assert load_window_state_rules(tmp_path).priorities == (100, 100)
    assert [r["priority"] for r in list_window_state_rules(tmp_path)["rules"]] == [
        100,
        100,
    ]
    with pytest.raises(ValueError):
        save("bad", priority=True)
    assert not (tmp_path / "assets/bad.png").exists()


@pytest.mark.parametrize("found", [False, True])
def test_priority_miss_descends_and_all_miss_checks_everything(
    tmp_path, monkeypatch, found
):
    """高层未命中才下探，无命中时全部完成，并在下一轮重查高层。"""
    templates = []
    for i in (1, 2):
        p = tmp_path / f"{i}.png"
        Image.new("RGB", (4, 4), (i, 0, 0)).save(p)
        templates.append(ImageTemplate(str(p)))
    calls = []

    def match(**kw):
        """仅最低层按参数命中。"""
        i = kw["template"].image.getpixel((0, 0))[0]
        calls.append(i)
        m = ImageMatch(Rect(0, 0, 4, 4), 0.99) if i == 2 and found else None
        return adapter.LocatedTemplate(
            m, 0.99 if m else 0.1, None if m is None else m.rect
        )

    monkeypatch.setattr(adapter, "_locate_template", match)
    locator = adapter.PyAutoGuiScreenImageLocator(
        ScreenshotBackend(Image.new("RGB", (64, 64)))
    )
    requests = (
        ImageSearchRequest(templates[1], priority=0),
        ImageSearchRequest(templates[0], priority=100),
    )
    for _ in range(2):
        results = locator.locate_requests(requests, stop_on_priority_match=True)
        assert not any(r.skipped for r in results)
    assert calls == [1, 2, 1, 2]
    with pytest.raises(ValueError):
        locator.locate_requests(
            requests, stop_on_first_match=True, stop_on_priority_match=True
        )


@pytest.mark.parametrize("bad", [True, 1.5, "10", None])
def test_window_config_rejects_invalid_priority_and_conflicting_groups(
    tmp_path, preparation, bad
):
    """窗口配置显式坏优先级与同状态冲突必须拒绝。"""
    import json

    service, frame = preparation
    save_window_state_rule(
        tmp_path,
        service,
        frame_id=frame.id,
        crop=Rect(0, 0, 5, 5),
        name="one",
        state="页面",
    )
    path = tmp_path / "assets/window-states.json"
    data = json.loads(path.read_text())
    assert load_window_state_rules(tmp_path).priorities == (0,)
    data["groups"][0]["priority"] = bad
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="优先级"):
        load_window_state_rules(tmp_path)
    data["groups"][0]["priority"] = 0
    data["groups"].append(
        {
            "state": "页面",
            "priority": 100,
            "searches": [{"name": "other", "image": "one.png"}],
        }
    )
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="冲突"):
        load_window_state_rules(tmp_path)


def test_probe_priority_result_and_protocol_preserve_skipped(tmp_path, monkeypatch):
    """低层相似度即使可更高也不执行，候选与协议保留跳过和检查数。"""
    from game_automation.platform.local_desktop.entrypoints.desktop_backend import (
        observation_wire,
    )
    from game_automation.platform.macos.adapters.window_state_probe import (
        MacOSWindowStateProbe,
    )
    from game_automation.portable.application.state_observation import (
        ObservationPerformance,
        ObservationPhase,
        ObservationSample,
        ObservationSnapshot,
        StateObservation,
    )
    from game_automation.portable.application.window_state_rules import WindowStateRules
    from game_automation.portable.domain import ScreenStateCandidate
    from game_automation.portable.preparation.models import DesktopWindow
    from tests.test_state_observation import Probe, wait_until

    p = tmp_path / "high.png"
    Image.new("RGB", (4, 4)).save(p)
    rules = WindowStateRules(
        (
            ScreenStateCandidate("主页", ImageTemplate(str(tmp_path / "missing.png"))),
            ScreenStateCandidate("对话", ImageTemplate(str(p))),
        ),
        64,
        64,
        64,
        64,
        (0, 100),
    )

    def match(**kw):
        """对话以较低但达标的相似度命中。"""
        m = ImageMatch(Rect(0, 0, 4, 4), 0.92)
        return adapter.LocatedTemplate(m, 0.92, m.rect)

    monkeypatch.setattr(adapter, "_locate_template", match)
    backend = ScreenshotBackend(Image.new("RGB", (64, 64)))
    backend.close = lambda: None
    value = MacOSWindowStateProbe(
        DesktopWindow("42:1", "App", "页", Rect(0, 0, 64, 64)), rules, source=backend
    ).read()
    assert value.current_state == "对话" and value.candidates[0].skipped
    assert value.candidates[1].priority == 100 and backend.screenshot_calls == 1
    stats = ObservationPerformance().record(1, budget_ms=200, result=value)
    wire = observation_wire(
        ObservationSnapshot(
            phase=ObservationPhase.OBSERVING,
            sample=ObservationSample(1, 2, 3, value, 5),
            performance=stats,
        )
    )
    assert (
        wire["performance"]["checked_count"] == 1
        and wire["performance"]["skipped_count"] == 1
    )
    assert wire["evidence"][0]["skipped"] and wire["evidence"][0]["score"] is None
    probe = Probe()
    probe.value = value
    observer = StateObservation()
    try:
        observer.start(probe, hz=1, confirmations=2)
        wait_until(lambda: observer.snapshot().sequence == 1)
        assert (
            observer.snapshot().current_state == "未知"
            and observer.snapshot().candidate_state == "对话"
        )
        wait_until(lambda: observer.snapshot().current_state == "对话")
    finally:
        observer.stop()
