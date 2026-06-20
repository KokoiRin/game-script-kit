"""验证本地桌面平台 composition 装配。"""

from __future__ import annotations

import game_automation.platform.desktop.adapters as desktop
from game_automation.platform.local_desktop import composition
from game_automation.portable.domain import Click, Point, ScreenWindow, Script


def test_build_real_screen_image_locator_uses_desktop_adapter(monkeypatch) -> None:
    """验证本地桌面图像定位 factory 会延迟创建桌面 adapter。"""
    created = {}

    class FakeScreenImageLocator:
        def __init__(self) -> None:
            created["locator"] = self

    monkeypatch.setattr(desktop, "PyAutoGuiScreenImageLocator", FakeScreenImageLocator)

    locator = composition.build_real_screen_image_locator()

    assert locator is created["locator"]


def test_run_script_on_local_desktop_passes_screen_image_locator_factory(monkeypatch) -> None:
    """验证本地桌面运行脚本会把图像定位 factory 交给应用层。"""
    captured = {}
    script = Script(
        name="plain",
        window=ScreenWindow(),
        steps=(Click(Point(1, 2)),),
    )

    def fake_run_script(*args, **kwargs):
        """记录本地桌面 composition 传给应用层的参数。"""
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "result"

    monkeypatch.setattr(composition, "run_script", fake_run_script)

    result = composition.run_script_on_local_desktop(script, dry_run=True)

    assert result == "result"
    assert captured["kwargs"]["real_image_locator_factory"] is composition.build_real_screen_image_locator


def test_run_script_on_local_desktop_passes_screen_state_reader_factory(monkeypatch) -> None:
    """验证本地桌面运行脚本会把界面状态 reader factory 交给应用层。"""
    captured = {}
    script = Script(
        name="plain",
        window=ScreenWindow(),
        steps=(Click(Point(1, 2)),),
    )

    def fake_run_script(*args, **kwargs):
        """记录本地桌面 composition 传给应用层的参数。"""
        captured["kwargs"] = kwargs
        return "result"

    monkeypatch.setattr(composition, "run_script", fake_run_script)

    result = composition.run_script_on_local_desktop(script, dry_run=False)

    assert result == "result"
    assert captured["kwargs"]["real_screen_state_reader_factory"] is composition.build_real_screen_state_reader


def test_build_real_screen_state_reader_uses_local_control_application(monkeypatch) -> None:
    """验证真实界面状态 reader 复用本地控制 application 的状态探测能力。"""
    created = {}

    class FakeLocalControlApplication:
        def __init__(self, **kwargs) -> None:
            """记录 composition 传入的 application 依赖。"""
            created["kwargs"] = kwargs

        def build_screen_state_reader(self):
            """返回可识别的 fake reader。"""
            return "reader"

    monkeypatch.setattr(composition, "LocalControlApplication", FakeLocalControlApplication)

    reader = composition.build_real_screen_state_reader()

    assert reader == "reader"
    assert created["kwargs"]["real_image_locator_factory"] is composition.build_real_screen_image_locator
    assert created["kwargs"]["real_image_batch_locator_factory"] is composition.build_real_screen_image_batch_locator


def test_build_local_control_application_passes_batch_image_locator_factory(monkeypatch) -> None:
    """验证本地控制 UI 会装配批量图像定位 factory。"""
    captured = {}

    class FakeLocalControlApplication:
        def __init__(self, **kwargs) -> None:
            """记录 composition 传入的 application 依赖。"""
            captured["kwargs"] = kwargs

    monkeypatch.setattr(composition, "LocalControlApplication", FakeLocalControlApplication)

    app = composition.build_local_control_application()

    assert isinstance(app, FakeLocalControlApplication)
    assert captured["kwargs"]["real_image_locator_factory"] is composition.build_real_screen_image_locator
    assert captured["kwargs"]["real_image_batch_locator_factory"] is composition.build_real_screen_image_batch_locator
    assert captured["kwargs"]["screen_size_factory"] is composition.read_real_screen_size
