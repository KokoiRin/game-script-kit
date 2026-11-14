"""验证本地桌面平台 composition 装配。"""

from __future__ import annotations

import json

import game_automation.platform.desktop.adapters as desktop
from game_automation.platform.local_desktop import composition
from game_automation.portable.application.project_scripts import (
    ProjectScriptCatalogResult,
)
from game_automation.portable.application.task_discovery import TaskLoadError
from game_automation.portable.domain import (
    ImageBatchMatchResult,
    ImageMatch,
    Rect,
    ScreenWindow,
)
from tests.support.function_tasks import function_task


def test_build_real_screen_image_locator_uses_desktop_adapter(monkeypatch) -> None:
    """验证本地桌面图像定位 factory 会延迟创建桌面 adapter。"""
    created = {}

    class FakeScreenImageLocator:
        def __init__(self) -> None:
            """记录本例创建的识图替身。"""
            created["locator"] = self

    monkeypatch.setattr(desktop, "PyAutoGuiScreenImageLocator", FakeScreenImageLocator)

    locator = composition.build_real_screen_image_locator()

    assert locator is created["locator"]


def test_run_script_on_local_desktop_passes_screen_image_locator_factory(
    monkeypatch,
) -> None:
    """验证本地桌面运行脚本会把图像定位 factory 交给应用层。"""
    captured = {}
    script = function_task("plain", "ctx.click(Point(1, 2))", window=ScreenWindow())

    def fake_run_script(*args, **kwargs):
        """记录本地桌面 composition 传给应用层的参数。"""
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "result"

    monkeypatch.setattr(composition, "run_script", fake_run_script)

    result = composition.run_script_on_local_desktop(script, dry_run=True)

    assert result == "result"
    assert (
        captured["kwargs"]["real_image_locator_factory"]
        is composition.build_real_screen_image_locator
    )


def test_run_script_on_local_desktop_passes_target_application_activator(
    monkeypatch,
) -> None:
    """验证本地桌面运行会把目标应用和激活 factory 交给应用层。"""
    captured = {}
    script = function_task(
        "target-app", "ctx.click(Point(1, 2))", window=ScreenWindow()
    )

    def fake_run_script(*args, **kwargs):
        """记录本地桌面 composition 传给应用层的目标应用参数。"""
        captured["kwargs"] = kwargs
        return "result"

    monkeypatch.setattr(composition, "run_script", fake_run_script)

    result = composition.run_script_on_local_desktop(
        script,
        dry_run=False,
        target_application="Safari",
    )

    assert result == "result"
    assert captured["kwargs"]["target_application"] == "Safari"
    assert (
        captured["kwargs"]["real_application_activator_factory"]
        is composition.build_real_application_activator
    )


def test_build_real_application_activator_uses_macos_adapter(monkeypatch) -> None:
    """验证本地桌面激活 factory 会延迟创建 macOS adapter。"""
    import game_automation.platform.macos.adapters as macos

    created = {}

    class FakeApplicationActivator:
        def __init__(self) -> None:
            """记录 macOS adapter 创建。"""
            created["activator"] = self

    monkeypatch.setattr(macos, "MacOSApplicationActivator", FakeApplicationActivator)

    activator = composition.build_real_application_activator()

    assert activator is created["activator"]


def test_run_script_on_local_desktop_passes_target_window_controller(
    monkeypatch,
) -> None:
    """验证本地桌面运行会把窗口标题和控制 factory 交给应用层。"""
    captured = {}
    script = function_task(
        "target-window", "ctx.click(Point(1, 2))", window=ScreenWindow()
    )

    def fake_run_script(*args, **kwargs):
        """记录 composition 传给应用层的选窗参数。"""
        captured["kwargs"] = kwargs
        return "result"

    monkeypatch.setattr(composition, "run_script", fake_run_script)

    result = composition.run_script_on_local_desktop(
        script,
        dry_run=False,
        target_application="Safari",
        target_window_title="视觉自动化靶场",
    )

    assert result == "result"
    assert captured["kwargs"]["target_window_title"] == "视觉自动化靶场"
    assert (
        captured["kwargs"]["real_application_window_controller_factory"]
        is composition.build_real_application_window_controller
    )


def test_build_real_application_window_controller_uses_macos_adapter(
    monkeypatch,
) -> None:
    """验证本地桌面窗口控制 factory 会延迟创建 macOS adapter。"""
    import game_automation.platform.macos.adapters as macos

    created = {}

    class FakeWindowController:
        def __init__(self) -> None:
            """记录 macOS 窗口 adapter 创建。"""
            created["controller"] = self

    monkeypatch.setattr(macos, "MacOSApplicationWindowController", FakeWindowController)

    controller = composition.build_real_application_window_controller()

    assert controller is created["controller"]


def test_run_script_on_local_desktop_passes_screen_state_reader_factory(
    monkeypatch, tmp_path
) -> None:
    """验证本地桌面运行脚本会把界面状态 reader factory 交给应用层。"""
    captured = {}
    script = function_task("plain", "ctx.click(Point(1, 2))", window=ScreenWindow())

    def fake_run_script(*args, **kwargs):
        """记录本地桌面 composition 传给应用层的参数。"""
        captured["kwargs"] = kwargs
        return "result"

    monkeypatch.setattr(composition, "run_script", fake_run_script)
    monkeypatch.setattr(
        composition,
        "build_real_screen_state_reader",
        lambda **kwargs: kwargs["project_root"],
    )

    result = composition.run_script_on_local_desktop(
        script, dry_run=False, project_root=tmp_path
    )

    assert result == "result"
    assert captured["kwargs"]["real_screen_state_reader_factory"]() == tmp_path


def test_build_real_screen_state_reader_is_independent_of_local_control(
    monkeypatch,
) -> None:
    """脚本状态 reader 直接接平台识图能力，不创建 UI 应用或加载脚本目录。"""
    created = {}

    class FakeProjectScreenStateReader:
        def __init__(self, **kwargs) -> None:
            """记录 composition 传入的 application 依赖。"""
            created["kwargs"] = kwargs

    def reject_ui_construction():
        """阻止状态读取路径反向装配 UI。"""
        raise AssertionError("state reader must not construct local control")

    monkeypatch.setattr(
        composition, "ProjectScreenStateReader", FakeProjectScreenStateReader
    )
    monkeypatch.setattr(
        composition, "build_local_control_application", reject_ui_construction
    )

    reader = composition.build_real_screen_state_reader()

    assert isinstance(reader, FakeProjectScreenStateReader)
    assert created["kwargs"]["project_root"] == composition.PROJECT_ROOT
    assert (
        created["kwargs"]["real_image_locator_factory"]
        is composition.build_real_screen_image_locator
    )
    assert (
        created["kwargs"]["real_image_batch_locator_factory"]
        is composition.build_real_screen_image_batch_locator
    )


def test_build_local_control_application_passes_batch_image_locator_factory(
    monkeypatch,
) -> None:
    """验证本地控制 UI 会装配批量图像定位 factory。"""
    captured = {}

    class FakeLocalControlApplication:
        def __init__(self, **kwargs) -> None:
            """记录 composition 传入的 application 依赖。"""
            captured["kwargs"] = kwargs

    monkeypatch.setattr(
        composition, "LocalControlApplication", FakeLocalControlApplication
    )

    app = composition.build_local_control_application()

    assert isinstance(app, FakeLocalControlApplication)
    assert (
        captured["kwargs"]["real_image_locator_factory"]
        is composition.build_real_screen_image_locator
    )
    assert (
        captured["kwargs"]["real_image_batch_locator_factory"]
        is composition.build_real_screen_image_batch_locator
    )


def test_build_local_control_application_passes_project_script_catalog(
    monkeypatch,
) -> None:
    """验证本地控制 UI 会装配包含项目脚本的 catalog。"""
    captured = {}

    class FakeLocalControlApplication:
        def __init__(self, **kwargs) -> None:
            """记录 composition 传入的 application 依赖。"""
            captured["kwargs"] = kwargs

    def fake_load_project_script_catalog_result(project_root, **kwargs):
        """返回可识别的 fake catalog result。"""
        captured["project_root"] = project_root
        return ProjectScriptCatalogResult(
            catalog="catalog",
            script_config_errors=(TaskLoadError("bad.json", "bad"),),
        )

    monkeypatch.setattr(
        composition, "LocalControlApplication", FakeLocalControlApplication
    )
    monkeypatch.setattr(
        composition,
        "load_project_script_catalog_result",
        fake_load_project_script_catalog_result,
    )

    composition.build_local_control_application()

    assert captured["kwargs"]["catalog"] == "catalog"
    assert captured["kwargs"]["script_config_errors"] == (
        TaskLoadError("bad.json", "bad"),
    )
    assert captured["project_root"] == composition.PROJECT_ROOT


def test_real_screen_state_reader_reads_each_requested_workspace_configuration(
    tmp_path, monkeypatch
) -> None:
    """真实 reader 装配配合 fake 识图读取各自配置，不回落默认工作区或复用前一次目录。"""
    requests_seen = []

    class MatchingLocator:
        def locate_requests(self, requests, *, logger=None, stop_on_first_match=False):
            """记录真实 reader 解析的模板、区域与阈值，并返回命中。"""
            requests_seen.append(tuple(requests))
            assert stop_on_first_match is True
            return tuple(
                ImageBatchMatchResult(
                    request.template,
                    ImageMatch(Rect(10, 20, 30, 40), 0.95),
                    elapsed_ms=1,
                )
                for request in requests
            )

    def reject_catalog_loading(*args, **kwargs):
        """状态 reader 无需扫描脚本目录或装配控制台。"""
        raise AssertionError("screen state reader must not load a script catalog")

    monkeypatch.setattr(desktop, "PyAutoGuiScreenImageLocator", MatchingLocator)
    monkeypatch.setattr(
        composition, "load_project_script_catalog_result", reject_catalog_loading
    )

    for index, name in enumerate(("first", "second"), start=1):
        workspace = tmp_path / name
        assets = workspace / "assets"
        assets.mkdir(parents=True)
        image = assets / f"{name}-state.png"
        image.write_bytes(b"fake")
        region = {"left": index * 10, "top": 20, "width": 100, "height": 80}
        (assets / "screen-states.json").write_text(
            json.dumps(
                {
                    "regions": {"工作区区域": region},
                    "groups": [
                        {
                            "state": f"{name}主页",
                            "searches": [
                                {
                                    "name": f"{name}标识",
                                    "image": image.name,
                                    "region": "工作区区域",
                                    "min_confidence": 0.83,
                                }
                            ],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        reader = composition.build_real_screen_state_reader(project_root=workspace)

        assert reader.read_current_state(min_confidence=0.7) == f"{name}主页"
        assert len(requests_seen[-1]) == 1
        request = requests_seen[-1][0]
        assert request.template.path == str(image.resolve())
        assert request.region == Rect(**region)
        assert request.min_confidence == 0.83
    assert len(requests_seen) == 2
