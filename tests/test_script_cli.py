"""验证 star CLI 可以列出和按名称运行脚本。"""

import json
from types import ModuleType

from game_automation.portable.domain import (
    Click,
    Color,
    ImageMatch,
    ImageSearchSpec,
    ImageTarget,
    ImageTemplate,
    NamedImageSearch,
    Point,
    Rect,
    ScreenWindow,
    Script,
    SearchRef,
    ScreenStateCandidate,
    ScreenStateCandidateResult,
    ScreenStateProbeResult,
    TargetCatalog,
)
from game_automation.portable.engine.ports import InputDevice
from game_automation.portable.scripts_manager.catalog import ScriptCatalog
from game_automation.platform.local_desktop.entrypoints import cli
from game_automation.platform.local_desktop.entrypoints.cli import main


def test_star_cli_lists_available_scripts(capsys) -> None:
    """验证 list 子命令逐行输出已注册脚本。"""
    assert main(["list"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "demo",
        "recorded-clicks",
        "repeat-demo",
        "conditional-color-demo",
        "conditional-screen-state-demo",
        "wait-until-color-demo",
        "wait-until-image-demo",
        "click-image-demo",
        "click-leave-or-retry-loop",
    ]


def test_star_cli_runs_named_script_with_dry_run(capsys) -> None:
    """验证 dry-run 可以按名称运行指定脚本并打印操作。"""
    assert main(["run", "recorded-clicks", "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "wait 3s" in output
    assert "Point(x=242, y=92)" in output
    assert "Point(x=736, y=323)" in output
    assert "Point(x=741, y=400)" in output
    assert "wait 10s" in output


def test_star_cli_shows_script_details(capsys) -> None:
    """验证 details 子命令会展示脚本步骤和依赖检查。"""
    assert main(["details", "click-image-demo"]) == 0

    output = capsys.readouterr().out
    assert "脚本：click-image-demo" in output
    assert "步骤：" in output
    assert "- Click ImageTarget(assets/start.png, min_confidence=1)" in output
    assert "依赖：" in output
    assert "- 图片: assets/start.png" in output
    assert "图片依赖：" in output
    assert "- assets/start.png" in output
    assert "依赖检查：" in output


def test_star_cli_details_uses_screen_state_search_ref(monkeypatch, tmp_path, capsys) -> None:
    """验证 details 子命令会复用状态配置搜索别名。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "战斗失败",
                        "searches": [{"name": "离开按钮", "image": "离开.png"}],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = Script(
        name="shared-search-details-cli",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
    )
    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", ScriptCatalog((script,)))
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)

    assert main(["details", "shared-search-details-cli"]) == 0

    output = capsys.readouterr().out
    assert "脚本：shared-search-details-cli" in output
    assert 'Click ImageTarget(SearchRef("离开按钮"), min_confidence=1)' in output
    assert f"- {assets / '离开.png'}" in output
    assert "命名搜索已配置，图片文件可用" in output


def test_star_cli_details_reports_unknown_script(capsys) -> None:
    """验证 details 子命令会报告未知脚本。"""
    assert main(["details", "missing"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown script: missing" in captured.err


def test_star_cli_runs_repeat_demo_with_dry_run(capsys) -> None:
    """验证 repeat-demo 的 dry-run 会展开 Repeat 内部步骤。"""
    assert main(["run", "repeat-demo", "--dry-run"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "wait 2s",
        "click Point(x=120, y=180)",
        "wait 1s",
        "click Point(x=120, y=180)",
        "wait 1s",
        "click Point(x=120, y=180)",
        "wait 1s",
        "click Point(x=120, y=180)",
        "wait 1s",
        "click Point(x=120, y=180)",
        "wait 1s",
    ]


def test_star_cli_runs_conditional_color_demo_with_default_dry_run_color(capsys) -> None:
    """验证条件分支脚本 dry-run 默认固定颜色会走 else 分支。"""
    assert main(["run", "conditional-color-demo", "--dry-run"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "click Point(x=300, y=400)",
        "wait 0.5s",
    ]


def test_star_cli_runs_conditional_color_demo_with_custom_dry_run_color(capsys) -> None:
    """验证条件分支脚本 dry-run 可用指定颜色走 then 分支。"""
    assert main(["run", "conditional-color-demo", "--dry-run", "--dry-run-color", "#102030"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "click Point(x=100, y=200)",
        "wait 0.25s",
    ]


def test_star_cli_runs_conditional_screen_state_demo_with_default_dry_run_state(capsys) -> None:
    """验证状态条件分支脚本 dry-run 默认固定状态会走 else 分支。"""
    assert main(["run", "conditional-screen-state-demo", "--dry-run"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == ["wait 0.5s"]


def test_star_cli_runs_conditional_screen_state_demo_with_custom_dry_run_state(capsys) -> None:
    """验证状态条件分支脚本 dry-run 可用指定状态走 then 分支。"""
    assert main(
        [
            "run",
            "conditional-screen-state-demo",
            "--dry-run",
            "--dry-run-screen-state",
            "主页",
        ]
    ) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == ["click Point(x=100, y=200)"]


def test_star_cli_runs_dry_run_with_probed_screen_state(monkeypatch, capsys) -> None:
    """验证 CLI dry-run 可先探测当前状态再运行状态条件脚本。"""
    calls = []

    class FakeApp:
        def probe_screen_state_once(self, *, min_confidence=0.8, logger=None):
            """返回固定当前状态。"""
            calls.append(min_confidence)
            return ScreenStateProbeResult(
                candidates=(
                    ScreenStateCandidateResult(
                        candidate=ScreenStateCandidate("主页", ImageTemplate("assets/主页.png")),
                        match=ImageMatch(Rect(0, 0, 10, 10), confidence=0.9),
                        elapsed_ms=1.0,
                    ),
                ),
                elapsed_ms=1.0,
            )

    monkeypatch.setattr(cli, "build_local_control_application", lambda: FakeApp())

    assert main(["run", "conditional-screen-state-demo", "--dry-run", "--dry-run-probed-screen-state"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert calls == [0.8]
    assert captured.out.splitlines() == ["click Point(x=100, y=200)"]


def test_star_cli_rejects_probed_screen_state_without_dry_run(monkeypatch, capsys) -> None:
    """验证探测状态 dry-run 开关不能用于真实运行。"""
    calls = []
    monkeypatch.setattr(cli, "run_script_on_local_desktop", lambda *args, **kwargs: calls.append("run"))

    assert main(["run", "conditional-screen-state-demo", "--dry-run-probed-screen-state"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--dry-run-probed-screen-state requires --dry-run" in captured.err
    assert calls == []


def test_star_cli_rejects_conflicting_dry_run_screen_state_sources(monkeypatch, capsys) -> None:
    """验证手工状态和探测状态不能同时作为 dry-run 状态来源。"""
    calls = []
    monkeypatch.setattr(cli, "run_script_on_local_desktop", lambda *args, **kwargs: calls.append("run"))

    assert (
        main(
            [
                "run",
                "conditional-screen-state-demo",
                "--dry-run",
                "--dry-run-screen-state",
                "主页",
                "--dry-run-probed-screen-state",
            ]
        )
        == 2
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--dry-run-probed-screen-state conflicts with --dry-run-screen-state" in captured.err
    assert calls == []


def test_star_cli_reports_probed_screen_state_configuration_error(monkeypatch, capsys) -> None:
    """验证探测状态配置错误会阻止 dry-run 脚本执行。"""
    calls = []

    class FakeApp:
        def probe_screen_state_once(self, *, min_confidence=0.8, logger=None):
            """模拟状态配置非法。"""
            raise ValueError("bad screen state config")

    monkeypatch.setattr(cli, "build_local_control_application", lambda: FakeApp())
    monkeypatch.setattr(cli, "run_script_on_local_desktop", lambda *args, **kwargs: calls.append("run"))

    assert main(["run", "conditional-screen-state-demo", "--dry-run", "--dry-run-probed-screen-state"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "screen state probe configuration failed: bad screen state config" in captured.err
    assert calls == []


def test_star_cli_reports_probed_screen_state_runtime_error(monkeypatch, capsys) -> None:
    """验证探测状态运行错误会阻止 dry-run 脚本执行。"""
    calls = []

    class FakeApp:
        def probe_screen_state_once(self, *, min_confidence=0.8, logger=None):
            """模拟截图或图像定位失败。"""
            raise RuntimeError("image locator unavailable")

    monkeypatch.setattr(cli, "build_local_control_application", lambda: FakeApp())
    monkeypatch.setattr(cli, "run_script_on_local_desktop", lambda *args, **kwargs: calls.append("run"))

    assert main(["run", "conditional-screen-state-demo", "--dry-run", "--dry-run-probed-screen-state"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "screen state probe failed: image locator unavailable" in captured.err
    assert calls == []


def test_star_cli_does_not_probe_screen_state_for_unknown_script(monkeypatch, capsys) -> None:
    """验证未知脚本不会先触发真实界面状态探测。"""
    calls = []

    class FakeApp:
        def probe_screen_state_once(self, *, min_confidence=0.8, logger=None):
            """记录不应该发生的探测调用。"""
            calls.append("probe")
            return ScreenStateProbeResult(candidates=(), elapsed_ms=1.0)

    monkeypatch.setattr(cli, "build_local_control_application", lambda: FakeApp())

    assert main(["run", "missing", "--dry-run", "--dry-run-probed-screen-state"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown script: missing" in captured.err
    assert calls == []


def test_star_cli_reports_invalid_dry_run_color(capsys) -> None:
    """验证非法 dry-run 颜色会作为运行配置错误报告。"""
    assert main(["run", "conditional-color-demo", "--dry-run", "--dry-run-color", "bad"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "script run configuration failed: color must match" in captured.err


def test_star_cli_runs_wait_until_color_demo_with_custom_dry_run_color(capsys) -> None:
    """验证条件等待脚本 dry-run 可用指定颜色立即成功。"""
    assert main(["run", "wait-until-color-demo", "--dry-run", "--dry-run-color", "#102030"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "click Point(x=100, y=200)",
    ]


def test_star_cli_reports_wait_until_color_demo_timeout(capsys) -> None:
    """验证条件等待脚本 dry-run 默认颜色会超时并返回非零。"""
    assert main(["run", "wait-until-color-demo", "--dry-run"]) == 1

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "wait 0.5s",
        "wait 0.5s",
    ]
    assert "script run timed out: wait until condition timed out" in captured.err


def test_star_cli_runs_wait_until_image_demo_with_dry_run_image(capsys) -> None:
    """验证图片等待脚本 dry-run 可用指定模板立即成功。"""
    assert main(
        [
            "run",
            "wait-until-image-demo",
            "--dry-run",
            "--dry-run-image",
            "assets/start.png",
        ]
    ) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "click Point(x=100, y=200)",
    ]


def test_star_cli_reports_wait_until_image_demo_timeout(capsys) -> None:
    """验证图片等待脚本 dry-run 默认未找到会超时并返回非零。"""
    assert main(["run", "wait-until-image-demo", "--dry-run"]) == 1

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "wait 0.5s",
        "wait 0.5s",
    ]
    assert "script run timed out: wait until condition timed out" in captured.err


def test_star_cli_run_defaults_to_macos(monkeypatch, capsys) -> None:
    """验证 run 子命令默认使用 macOS adapter。"""
    clicks = []
    drags = []

    class FakeMacOSPointerDevice(InputDevice):
        def click(self, target) -> None:
            clicks.append(target)

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            drags.append((start, end, duration_seconds))

        def wait(self, duration_seconds: float) -> None:
            """dry-run 分支不等待。"""

    fake_macos_module = ModuleType("game_automation.platform.macos.adapters")
    fake_macos_module.MacOSPointerDevice = FakeMacOSPointerDevice
    monkeypatch.setitem(
        __import__("sys").modules,
        "game_automation.platform.macos.adapters",
        fake_macos_module,
    )

    assert main(["run", "recorded-clicks"]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert clicks == [
        Point(242, 92),
        Point(736, 323),
        Point(741, 400),
    ]
    assert drags == []


def test_star_cli_run_injects_color_reader_for_conditional_script(monkeypatch, capsys) -> None:
    """验证真实运行条件分支脚本时 CLI 会注入取色 adapter。"""
    import game_automation.platform.desktop.adapters as desktop

    clicks = []
    read_points = []

    class FakeMacOSPointerDevice(InputDevice):
        def click(self, target) -> None:
            """记录真实模式点击请求。"""
            clicks.append(target)

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """条件示例脚本不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """测试中不真实等待。"""

    class FakePixelColorReader:
        def __init__(self) -> None:
            """标记 fake 取色 reader 已创建。"""

        def read_color(self, point) -> Color:
            """记录读取点并返回 then 分支颜色。"""
            read_points.append(point)
            return Color.from_hex("#102030")

    fake_macos_module = ModuleType("game_automation.platform.macos.adapters")
    fake_macos_module.MacOSPointerDevice = FakeMacOSPointerDevice
    monkeypatch.setitem(
        __import__("sys").modules,
        "game_automation.platform.macos.adapters",
        fake_macos_module,
    )
    monkeypatch.setattr(desktop, "PyAutoGuiPixelColorReader", FakePixelColorReader)
    monkeypatch.setitem(__import__("sys").modules, "game_automation.platform.desktop.adapters", desktop)

    assert main(["run", "conditional-color-demo"]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert read_points == [Point(50, 60)]
    assert clicks == [Point(100, 200)]


def test_star_cli_run_reports_color_reader_setup_error(monkeypatch, capsys) -> None:
    """验证真实运行条件分支脚本时取色 adapter setup 失败会被报告。"""
    import game_automation.platform.desktop.adapters as desktop

    class FailingPixelColorReader:
        def __init__(self) -> None:
            """模拟取色 adapter 初始化失败。"""
            raise RuntimeError("screen color unavailable")

    monkeypatch.setattr(desktop, "PyAutoGuiPixelColorReader", FailingPixelColorReader)
    monkeypatch.setitem(__import__("sys").modules, "game_automation.platform.desktop.adapters", desktop)

    assert main(["run", "conditional-color-demo"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "script run setup failed: screen color unavailable" in captured.err


def test_star_cli_run_injects_image_locator_for_image_script(monkeypatch, capsys) -> None:
    """验证真实运行图片条件脚本时 CLI 会注入图像定位 adapter。"""
    import game_automation.platform.desktop.adapters as desktop

    clicks = []
    located_templates = []

    class FakeMacOSPointerDevice(InputDevice):
        def click(self, target) -> None:
            """记录真实模式点击请求。"""
            clicks.append(target)

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """图片示例脚本不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """测试中不真实等待。"""

    class FakeScreenImageLocator:
        def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
            """记录模板并返回图片存在。"""
            located_templates.append(template)
            return ImageMatch(Rect(0, 0, 1, 1), confidence=1.0)

    fake_macos_module = ModuleType("game_automation.platform.macos.adapters")
    fake_macos_module.MacOSPointerDevice = FakeMacOSPointerDevice
    monkeypatch.setitem(
        __import__("sys").modules,
        "game_automation.platform.macos.adapters",
        fake_macos_module,
    )
    monkeypatch.setattr(desktop, "PyAutoGuiScreenImageLocator", FakeScreenImageLocator)
    monkeypatch.setitem(__import__("sys").modules, "game_automation.platform.desktop.adapters", desktop)

    assert main(["run", "wait-until-image-demo"]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert located_templates == [ImageTemplate("assets/start.png")]
    assert clicks == [Point(100, 200)]


def test_star_cli_runs_click_image_demo_with_dry_run_image(capsys) -> None:
    """验证图片目标点击 demo 可用 dry-run 图片配置解析点击坐标。"""
    assert main(
        [
            "run",
            "click-image-demo",
            "--dry-run",
            "--dry-run-image",
            "assets/start.png",
        ]
    ) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "click Point(x=0, y=0)",
    ]


def test_star_cli_runs_click_image_demo_with_script_images(capsys) -> None:
    """验证 CLI 可自动用脚本图片依赖作为 dry-run 命中图片。"""
    assert main(["run", "click-image-demo", "--dry-run", "--dry-run-script-images"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "click Point(x=0, y=0)",
    ]


def test_star_cli_uses_screen_state_search_ref_for_dry_run(monkeypatch, tmp_path, capsys) -> None:
    """验证 CLI dry-run 可复用状态配置里的搜索别名。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "战斗失败",
                        "searches": [
                            {
                                "name": "离开按钮",
                                "image": "离开.png",
                                "min_confidence": 0.75,
                            },
                        ],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = Script(
        name="shared-search-cli",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
    )
    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", ScriptCatalog((script,)))
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)

    assert main(
        [
            "run",
            "shared-search-cli",
            "--dry-run",
            "--dry-run-image",
            str(assets / "离开.png"),
        ]
    ) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.splitlines() == ["click Point(x=0, y=0)"]


def test_star_cli_uses_screen_state_search_ref_with_script_images(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    """验证自动图片依赖会解析状态配置搜索别名。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "离开.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "战斗失败",
                        "searches": [{"name": "离开按钮", "image": "离开.png"}],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = Script(
        name="shared-search-auto-images",
        window=ScreenWindow(),
        steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
    )
    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", ScriptCatalog((script,)))
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)

    assert main(["run", "shared-search-auto-images", "--dry-run", "--dry-run-script-images"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.splitlines() == ["click Point(x=0, y=0)"]


def test_star_cli_local_search_ref_overrides_screen_state_config(monkeypatch, tmp_path, capsys) -> None:
    """验证 CLI 中脚本局部搜索别名覆盖状态配置同名搜索。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "配置.png").write_bytes(b"fake")
    (assets / "脚本.png").write_bytes(b"fake")
    (assets / "screen-states.json").write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "state": "战斗失败",
                        "searches": [{"name": "离开按钮", "image": "配置.png"}],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    script = Script(
        name="local-search-cli",
        window=ScreenWindow(),
        resources=TargetCatalog(
            searches=(
                NamedImageSearch(
                    "离开按钮",
                    ImageSearchSpec(ImageTemplate("assets/脚本.png")),
                ),
            ),
        ),
        steps=(Click(ImageTarget(SearchRef("离开按钮"))),),
    )
    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", ScriptCatalog((script,)))
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)

    assert main(
        [
            "run",
            "local-search-cli",
            "--dry-run",
            "--dry-run-image",
            "assets/脚本.png",
        ]
    ) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.splitlines() == ["click Point(x=0, y=0)"]


def test_star_cli_rejects_script_images_without_dry_run(capsys) -> None:
    """验证自动 dry-run 图片依赖开关不能用于真实运行。"""
    assert main(["run", "click-image-demo", "--dry-run-script-images"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--dry-run-script-images requires --dry-run" in captured.err


def test_star_cli_probe_state_outputs_current_state(monkeypatch, capsys) -> None:
    """验证 probe-state 子命令输出当前状态和候选结果。"""
    calls = []

    class FakeApp:
        def probe_screen_state_once(self, *, min_confidence=0.8, logger=None):
            """记录最低置信度并返回固定状态探测结果。"""
            calls.append(min_confidence)
            return ScreenStateProbeResult(
                candidates=(
                    ScreenStateCandidateResult(
                        candidate=ScreenStateCandidate(
                            "主页",
                            ImageTemplate("assets/主页.png"),
                            search_name="主页标识",
                        ),
                        match=ImageMatch(Rect(10, 20, 30, 40), confidence=0.91),
                        elapsed_ms=4.0,
                    ),
                    ScreenStateCandidateResult(
                        candidate=ScreenStateCandidate(
                            "人物",
                            ImageTemplate("assets/人物.png"),
                            search_name="人物标识",
                        ),
                        match=None,
                        elapsed_ms=3.0,
                    ),
                ),
                elapsed_ms=7.0,
            )

    monkeypatch.setattr(cli, "build_local_control_application", lambda: FakeApp())

    assert main(["probe-state"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert calls == [0.8]
    assert captured.out.splitlines() == [
        "当前状态：主页",
        "总耗时：7.00ms",
        "候选：",
        "- 主页 / 主页标识：命中；耗时 4.00ms；置信度 0.910",
        "- 人物 / 人物标识：未命中；耗时 3.00ms；置信度 无",
    ]


def test_star_cli_probe_state_outputs_json(monkeypatch, capsys) -> None:
    """验证 probe-state 可以输出机器可读 JSON。"""
    calls = []

    class FakeApp:
        def probe_screen_state_once(self, *, min_confidence=0.8, logger=None):
            """记录最低置信度并返回含三种候选状态的探测结果。"""
            calls.append(min_confidence)
            return ScreenStateProbeResult(
                candidates=(
                    ScreenStateCandidateResult(
                        candidate=ScreenStateCandidate(
                            "主页",
                            ImageTemplate("assets/主页.png"),
                            search_name="主页标识",
                        ),
                        match=ImageMatch(Rect(10, 20, 30, 40), confidence=0.91),
                        elapsed_ms=4.0,
                    ),
                    ScreenStateCandidateResult(
                        candidate=ScreenStateCandidate(
                            "人物",
                            ImageTemplate("assets/人物.png"),
                            search_name="人物标识",
                        ),
                        match=None,
                        elapsed_ms=3.0,
                    ),
                    ScreenStateCandidateResult(
                        candidate=ScreenStateCandidate("装备", ImageTemplate("assets/装备.png")),
                        match=None,
                        elapsed_ms=0.0,
                        skipped=True,
                    ),
                ),
                elapsed_ms=7.0,
            )

    monkeypatch.setattr(cli, "build_local_control_application", lambda: FakeApp())

    assert main(["probe-state", "--json", "--min-confidence", "0.75"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert calls == [0.75]
    assert json.loads(captured.out) == {
        "current_state": "主页",
        "known": True,
        "elapsed_ms": 7.0,
        "candidates": [
            {
                "name": "主页",
                "search_name": "主页标识",
                "status": "matched",
                "elapsed_ms": 4.0,
                "confidence": 0.91,
            },
            {
                "name": "人物",
                "search_name": "人物标识",
                "status": "missed",
                "elapsed_ms": 3.0,
                "confidence": None,
            },
            {
                "name": "装备",
                "search_name": None,
                "status": "skipped",
                "elapsed_ms": 0.0,
                "confidence": None,
            },
        ],
    }


def test_star_cli_probe_state_uses_min_confidence(monkeypatch, capsys) -> None:
    """验证 probe-state 子命令会传递最低置信度。"""
    calls = []

    class FakeApp:
        def probe_screen_state_once(self, *, min_confidence=0.8, logger=None):
            """记录调用参数并返回未知状态。"""
            calls.append(min_confidence)
            return ScreenStateProbeResult(candidates=(), elapsed_ms=1.5)

    monkeypatch.setattr(cli, "build_local_control_application", lambda: FakeApp())

    assert main(["probe-state", "--min-confidence", "0.75"]) == 0

    assert calls == [0.75]
    assert "当前状态：未知" in capsys.readouterr().out


def test_star_cli_probe_state_reports_configuration_error(monkeypatch, capsys) -> None:
    """验证 probe-state 会报告状态配置错误。"""

    class FakeApp:
        def probe_screen_state_once(self, *, min_confidence=0.8, logger=None):
            """模拟配置解析失败。"""
            raise ValueError("bad screen state config")

    monkeypatch.setattr(cli, "build_local_control_application", lambda: FakeApp())

    assert main(["probe-state"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "screen state probe configuration failed: bad screen state config" in captured.err


def test_star_cli_probe_state_reports_runtime_error(monkeypatch, capsys) -> None:
    """验证 probe-state 会报告截图或图像定位运行错误。"""

    class FakeApp:
        def probe_screen_state_once(self, *, min_confidence=0.8, logger=None):
            """模拟图像定位 adapter 不可用。"""
            raise RuntimeError("image locator unavailable")

    monkeypatch.setattr(cli, "build_local_control_application", lambda: FakeApp())

    assert main(["probe-state"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "screen state probe failed: image locator unavailable" in captured.err


def test_star_cli_reports_click_image_demo_missing_target(capsys) -> None:
    """验证图片目标点击 demo 未配置 dry-run 图片时报告未找到。"""
    assert main(["run", "click-image-demo", "--dry-run"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "script run failed: image target not found: assets/start.png" in captured.err


def test_star_cli_reports_unknown_script(capsys) -> None:
    """验证未知脚本名称会返回非零退出码并写入 stderr。"""
    assert main(["run", "missing", "--dry-run"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown script: missing" in captured.err


def test_star_cli_ui_starts_local_control_without_opening_browser(monkeypatch, capsys) -> None:
    """验证 ui 子命令会把 host/port/no-open 参数传给本地 UI 入口。"""
    import game_automation.platform.local_desktop.entrypoints.local_ui as local_ui

    calls = []

    def fake_serve_local_control_ui(*, host, port, open_browser):
        calls.append(
            {
                "host": host,
                "port": port,
                "open_browser": open_browser,
            }
        )
        return 0

    monkeypatch.setattr(local_ui, "serve_local_control_ui", fake_serve_local_control_ui)

    assert main(["ui", "--host", "127.0.0.1", "--port", "8765", "--no-open"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert calls == [
        {
            "host": "127.0.0.1",
            "port": 8765,
            "open_browser": False,
        }
    ]


def test_star_cli_ui_help_does_not_start_local_control(capsys) -> None:
    """验证 ui help 只展示参数，不启动本地服务。"""
    try:
        main(["ui", "--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "--no-open" in captured.out
    assert "Star control UI:" not in captured.out


def test_star_cli_recorder_injects_color_reader(monkeypatch) -> None:
    """验证 recorder 子命令会组装坐标、按键和取色 adapter。"""
    import game_automation.platform.desktop.adapters as desktop
    import game_automation.portable.tools.coordinate_recorder as recorder_module

    created = {}

    class FakePointerReader:
        def __init__(self) -> None:
            """标记 fake 坐标 reader 已创建。"""
            created["pointer"] = self

    class FakeKeyReader:
        def __init__(self) -> None:
            """标记 fake 按键 reader 已创建。"""
            created["key"] = self
            self.closed = False

        def close(self) -> None:
            """记录 CLI finally 会关闭按键 reader。"""
            self.closed = True

    class FakeColorReader:
        def __init__(self) -> None:
            """标记 fake 取色 reader 已创建。"""
            created["color"] = self

    class FakeRecorder:
        def __init__(self, *, pointer_reader, key_reader, color_reader, **kwargs) -> None:
            """捕获 CLI 注入到 recorder 的依赖。"""
            created["recorder_args"] = (pointer_reader, key_reader, color_reader, kwargs)

        def run(self) -> None:
            """让测试中的 recorder 立即结束。"""

    monkeypatch.setattr(desktop, "PyAutoGuiPointerPositionReader", FakePointerReader)
    monkeypatch.setattr(desktop, "TerminalKeyStateReader", FakeKeyReader)
    monkeypatch.setattr(desktop, "PyAutoGuiPixelColorReader", FakeColorReader)
    monkeypatch.setattr(recorder_module, "CoordinateRecorder", FakeRecorder)
    monkeypatch.setitem(__import__("sys").modules, "game_automation.platform.desktop.adapters", desktop)
    monkeypatch.setitem(
        __import__("sys").modules,
        "game_automation.portable.tools.coordinate_recorder",
        recorder_module,
    )

    assert main(["recorder"]) == 0

    pointer_reader, key_reader, color_reader, kwargs = created["recorder_args"]
    assert pointer_reader is created["pointer"]
    assert key_reader is created["key"]
    assert color_reader is created["color"]
    assert kwargs["display_interval_seconds"] == 1.0
    assert kwargs["poll_interval_seconds"] == 0.05
    assert created["key"].closed is True


def test_star_cli_recorder_reports_color_reader_setup_error(monkeypatch, capsys) -> None:
    """验证取色 adapter 初始化失败时 CLI 返回 setup 错误。"""
    import game_automation.platform.desktop.adapters as desktop
    class FakePointerReader:
        def __init__(self) -> None:
            """创建 fake 坐标 reader。"""

    class FakeKeyReader:
        def __init__(self) -> None:
            """创建 fake 按键 reader。"""
            self.closed = False

        def close(self) -> None:
            """记录按键 reader 被关闭。"""
            self.closed = True

    class FailingColorReader:
        def __init__(self) -> None:
            """模拟取色 adapter setup 失败。"""
            raise RuntimeError("screen color unavailable")

    monkeypatch.setattr(desktop, "PyAutoGuiPointerPositionReader", FakePointerReader)
    monkeypatch.setattr(desktop, "TerminalKeyStateReader", FakeKeyReader)
    monkeypatch.setattr(desktop, "PyAutoGuiPixelColorReader", FailingColorReader)
    monkeypatch.setitem(__import__("sys").modules, "game_automation.platform.desktop.adapters", desktop)

    assert main(["recorder"]) == 1

    captured = capsys.readouterr()
    assert "coordinate recorder setup failed: screen color unavailable" in captured.err
