"""验证 star CLI 可以列出和按名称运行脚本。"""

import json
from types import ModuleType

import pytest

from game_automation.portable.application.project_assets import SCRIPT_FOLDER
from game_automation.portable.application.script_run import ScriptRunResult
from game_automation.portable.domain import (
    Click,
    Color,
    ImageMatch,
    ImageSearchSpec,
    ImageTarget,
    ImageTemplate,
    NamedImageSearch,
    Point,
    PointRef,
    Rect,
    ScreenWindow,
    Script,
    SearchRef,
    TargetCatalog,
)
from game_automation.portable.engine.ports import InputDevice
from game_automation.portable.scripts_manager.catalog import ScriptCatalog
from game_automation.platform.local_desktop.entrypoints import cli
from game_automation.platform.local_desktop.entrypoints.cli import main


def _script_run_result(exit_code: int, finish_reason: str) -> ScriptRunResult:
    """构造 CLI 测试用脚本运行结果。"""
    return ScriptRunResult(exit_code=exit_code, finish_reason=finish_reason)


def test_file_hotkey_runs_in_order_in_dry_run(monkeypatch, tmp_path, capsys) -> None:
    """文件脚本在循环中粘贴时，模拟运行应按顺序显示等待与 Command+V。"""
    script_dir = tmp_path / SCRIPT_FOLDER
    script_dir.mkdir()
    (script_dir / "paste.json").write_text(json.dumps({
        "name": "粘贴测试",
        "steps": [{"wait": 0.2}, {"repeat": {
            "times": 2, "steps": [{"hotkey": ["command", "v"]}],
        }}],
    }), encoding="utf-8")
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)

    assert main(["run", "粘贴测试", "--dry-run"]) == 0

    assert capsys.readouterr().out.splitlines() == [
        "wait 0.2s", "hotkey command+v", "hotkey command+v",
    ]


def test_star_cli_lists_available_scripts(capsys) -> None:
    """验证 list 子命令逐行输出已注册脚本。"""
    assert main(["list"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output[:11] == [
        "demo",
        "recorded-clicks",
        "repeat-demo",
        "conditional-color-demo",
        "conditional-screen-state-demo",
        "wait-until-color-demo",
        "wait-until-image-demo",
        "wait-until-screen-state-demo",
        "click-image-demo",
        "click-leave-or-retry-loop",
        "file-script-demo",
    ]


def test_star_cli_lists_file_backed_scripts(monkeypatch, tmp_path, capsys) -> None:
    """验证 list 子命令会列出项目脚本目录中的 JSON 脚本。"""
    script_dir = tmp_path / SCRIPT_FOLDER
    script_dir.mkdir()
    (script_dir / "user.json").write_text(
        '{"name": "用户脚本", "steps": [{"wait": 1}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", ScriptCatalog((Script("builtin", ScreenWindow(), (Click(Point(1, 2)),)),)))

    assert main(["list"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == ["builtin", "用户脚本"]


def test_star_cli_lists_good_scripts_and_reports_bad_file(monkeypatch, tmp_path, capsys) -> None:
    """验证 list 子命令隔离坏脚本并把配置错误写入 stderr。"""
    script_dir = tmp_path / SCRIPT_FOLDER
    script_dir.mkdir()
    (script_dir / "good.json").write_text(
        '{"name": "good", "steps": [{"wait": 1}]}',
        encoding="utf-8",
    )
    (script_dir / "bad.json").write_text(
        '{"name": "bad", "steps": [{"drag": {}}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", ScriptCatalog((Script("builtin", ScreenWindow(), (Click(Point(1, 2)),)),)))

    assert main(["list"]) == 0

    captured = capsys.readouterr()
    assert captured.out.splitlines() == ["builtin", "good"]
    assert "脚本配置错误：" in captured.err
    assert "bad.json: unsupported step type: drag" in captured.err


def test_star_cli_details_describes_file_backed_script(monkeypatch, tmp_path, capsys) -> None:
    """验证 details 子命令可以展示文件脚本步骤和依赖。"""
    script_dir = tmp_path / SCRIPT_FOLDER
    script_dir.mkdir()
    (script_dir / "user.json").write_text(
        json.dumps(
            {
                "name": "用户脚本",
                "resources": {"points": {"头像": {"x": 242, "y": 92}}},
                "steps": [{"click": {"point": "头像"}}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", ScriptCatalog(()))

    assert main(["details", "用户脚本"]) == 0

    output = capsys.readouterr().out
    assert "脚本：用户脚本" in output
    assert 'Click PointRef("头像")' in output
    assert "点位依赖：" in output
    assert "- 头像" in output


def test_star_cli_runs_file_backed_script_in_dry_run(monkeypatch, tmp_path) -> None:
    """验证 run 子命令可以 dry-run 运行文件脚本。"""
    script_dir = tmp_path / SCRIPT_FOLDER
    script_dir.mkdir()
    (script_dir / "user.json").write_text(
        '{"name": "用户脚本", "steps": [{"wait": 0}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", ScriptCatalog(()))

    assert main(["run", "用户脚本", "--dry-run"]) == 0


def test_star_cli_run_plan_runs_scripts_in_order(monkeypatch, capsys) -> None:
    """验证 run-plan 子命令会按给定顺序运行多个脚本。"""
    calls = []
    catalog = ScriptCatalog(
        (
            Script("first", ScreenWindow(), (Click(Point(1, 2)),)),
            Script("second", ScreenWindow(), (Click(Point(3, 4)),)),
        )
    )

    def fake_run(script, **kwargs):
        """记录脚本并模拟成功运行。"""
        calls.append((script.name, kwargs["dry_run"]))
        print(f"ran {script.name}")
        return _script_run_result(0, "completed")

    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", catalog)
    monkeypatch.setattr(cli, "run_script_on_local_desktop", fake_run)

    assert main(["run-plan", "first", "second", "--dry-run"]) == 0

    captured = capsys.readouterr()
    assert calls == [("first", True), ("second", True)]
    assert "[1] first: exit_code=0 finish_reason=completed" in captured.out
    assert "[2] second: exit_code=0 finish_reason=completed" in captured.out
    assert "ran first" in captured.out
    assert "ran second" in captured.out
    assert captured.err == ""


def test_star_cli_run_plan_passes_target_application_to_every_script(monkeypatch) -> None:
    """验证 run-plan 会在每个脚本项运行时传递同一目标应用。"""
    calls = []
    catalog = ScriptCatalog(
        (
            Script("first", ScreenWindow(), (Click(Point(1, 2)),)),
            Script("second", ScreenWindow(), (Click(Point(3, 4)),)),
        )
    )

    def fake_run(script, **kwargs):
        """记录每个脚本收到的目标应用。"""
        calls.append((script.name, kwargs["target_application"]))
        return _script_run_result(0, "completed")

    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", catalog)
    monkeypatch.setattr(cli, "run_script_on_local_desktop", fake_run)

    assert main(["run-plan", "first", "second", "--target-app", "Safari"]) == 0
    assert calls == [("first", "Safari"), ("second", "Safari")]


def test_star_cli_run_plan_passes_target_window_to_every_script(monkeypatch) -> None:
    """验证 run-plan 为每个脚本项传递同一目标窗口标题。"""
    calls = []
    catalog = ScriptCatalog(
        (
            Script("first", ScreenWindow(), (Click(Point(1, 2)),)),
            Script("second", ScreenWindow(), (Click(Point(3, 4)),)),
        )
    )

    def fake_run(script, **kwargs):
        """记录每个脚本收到的窗口标题。"""
        calls.append((script.name, kwargs["target_window_title"]))
        return _script_run_result(0, "completed")

    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", catalog)
    monkeypatch.setattr(cli, "run_script_on_local_desktop", fake_run)

    assert main(
        [
            "run-plan",
            "first",
            "second",
            "--target-app",
            "Safari",
            "--target-window-title",
            "视觉自动化靶场",
        ]
    ) == 0
    assert calls == [
        ("first", "视觉自动化靶场"),
        ("second", "视觉自动化靶场"),
    ]


def test_star_cli_run_plan_rejects_target_application_in_dry_run(monkeypatch, capsys) -> None:
    """验证 run-plan dry-run 不允许请求真实应用激活。"""
    calls = []
    monkeypatch.setattr(cli, "run_script_on_local_desktop", lambda *args, **kwargs: calls.append(True))

    assert main(["run-plan", "first", "--dry-run", "--target-app", "Safari"]) == 2

    captured = capsys.readouterr()
    assert "--target-app cannot be used with --dry-run" in captured.err
    assert calls == []


def test_star_cli_run_plan_stops_after_first_error(monkeypatch, capsys) -> None:
    """验证 run-plan 默认遇到失败脚本后停止。"""
    calls = []
    catalog = ScriptCatalog(
        (
            Script("first", ScreenWindow(), (Click(Point(1, 2)),)),
            Script("second", ScreenWindow(), (Click(Point(3, 4)),)),
        )
    )

    def fake_run(script, **kwargs):
        """让第一个脚本失败。"""
        calls.append(script.name)
        return _script_run_result(1 if script.name == "first" else 0, "failed")

    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", catalog)
    monkeypatch.setattr(cli, "run_script_on_local_desktop", fake_run)

    assert main(["run-plan", "first", "second", "--dry-run"]) == 1

    captured = capsys.readouterr()
    assert calls == ["first"]
    assert "[1] first: exit_code=1 finish_reason=failed" in captured.out
    assert "[2] second" not in captured.out


def test_star_cli_run_plan_can_continue_after_error(monkeypatch, capsys) -> None:
    """验证 run-plan 可在失败后继续收集后续脚本结果。"""
    calls = []
    catalog = ScriptCatalog(
        (
            Script("first", ScreenWindow(), (Click(Point(1, 2)),)),
            Script("second", ScreenWindow(), (Click(Point(3, 4)),)),
        )
    )

    def fake_run(script, **kwargs):
        """让第一个脚本失败，第二个成功。"""
        calls.append(script.name)
        return _script_run_result(1 if script.name == "first" else 0, "failed" if script.name == "first" else "completed")

    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", catalog)
    monkeypatch.setattr(cli, "run_script_on_local_desktop", fake_run)

    assert main(["run-plan", "first", "second", "--dry-run", "--continue-on-error"]) == 1

    captured = capsys.readouterr()
    assert calls == ["first", "second"]
    assert "[1] first: exit_code=1 finish_reason=failed" in captured.out
    assert "[2] second: exit_code=0 finish_reason=completed" in captured.out


def test_star_cli_run_plan_reports_unmet_condition_without_running_later_scripts(monkeypatch, capsys) -> None:
    """验证 run-plan 不会把条件未满足误报为整轮完成。"""
    calls = []
    catalog = ScriptCatalog(
        (
            Script("first", ScreenWindow(), (Click(Point(1, 2)),)),
            Script("second", ScreenWindow(), (Click(Point(3, 4)),)),
        )
    )

    def fake_run(script, **kwargs):
        """让第一个脚本因条件未满足正常停止。"""
        calls.append(script.name)
        return _script_run_result(0, "stopped_unmet_condition")

    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", catalog)
    monkeypatch.setattr(cli, "run_script_on_local_desktop", fake_run)

    assert main(["run-plan", "first", "second", "--dry-run"]) == 0

    captured = capsys.readouterr()
    assert calls == ["first"]
    assert "Run Plan: exit_code=0 finish_reason=stopped_unmet_condition" in captured.out
    assert "[1] first: exit_code=0 finish_reason=stopped_unmet_condition" in captured.out
    assert "[2] second" not in captured.out


def test_star_cli_run_plan_uses_each_script_image_dependencies(monkeypatch, tmp_path) -> None:
    """验证 run-plan 自动图片 dry-run 会按每个脚本解析自己的图片依赖。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    first_image = assets / "first.png"
    second_image = assets / "second.png"
    first_image.write_bytes(b"fake")
    second_image.write_bytes(b"fake")
    calls = []
    catalog = ScriptCatalog(
        (
            Script("first", ScreenWindow(), (Click(ImageTarget(ImageTemplate(str(first_image)))),)),
            Script("second", ScreenWindow(), (Click(ImageTarget(ImageTemplate(str(second_image)))),)),
        )
    )

    def fake_run(script, **kwargs):
        """记录每个脚本收到的 dry-run 图片集合。"""
        calls.append((script.name, kwargs["dry_run_images"]))
        return _script_run_result(0, "completed")

    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", catalog)
    monkeypatch.setattr(cli, "run_script_on_local_desktop", fake_run)

    assert main(["run-plan", "first", "second", "--dry-run", "--dry-run-script-images"]) == 0

    assert calls == [
        ("first", (str(first_image),)),
        ("second", (str(second_image),)),
    ]


def test_star_cli_run_plan_rejects_unknown_script_before_running(monkeypatch, capsys) -> None:
    """验证 run-plan 遇到未知脚本时不会运行后续脚本。"""
    calls = []
    monkeypatch.setattr(
        cli,
        "DEFAULT_SCRIPT_CATALOG",
        ScriptCatalog((Script("second", ScreenWindow(), (Click(Point(3, 4)),)),)),
    )
    monkeypatch.setattr(cli, "run_script_on_local_desktop", lambda *args, **kwargs: calls.append("run"))

    assert main(["run-plan", "missing", "second", "--dry-run"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown script: missing" in captured.err
    assert calls == []


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


def test_star_cli_details_shows_point_dependencies(monkeypatch, capsys) -> None:
    """验证 details 子命令会展示结构化点位依赖。"""
    script = Script(
        name="point-dependency-cli",
        window=ScreenWindow(),
        steps=(Click(PointRef("头像")), Click(PointRef("头像")), Click(Point(100, 200))),
    )
    monkeypatch.setattr(cli, "DEFAULT_SCRIPT_CATALOG", ScriptCatalog((script,)))

    assert main(["details", "point-dependency-cli"]) == 0

    output = capsys.readouterr().out
    assert "点位依赖：" in output
    assert "- 头像" in output
    assert "- Point(x=100, y=200)" not in output


def test_star_cli_shows_wait_until_screen_state_details(capsys) -> None:
    """验证 details 子命令会展示状态等待步骤和状态依赖。"""
    assert main(["details", "wait-until-screen-state-demo"]) == 0

    output = capsys.readouterr().out
    assert "脚本：wait-until-screen-state-demo" in output
    assert 'WaitUntil ScreenStateIs("主页") timeout=1s interval=0.5s' in output
    assert "状态等待：" in output
    assert "- 等待状态: 主页" in output
    assert "- 状态: 主页" in output
    assert "[OK] 状态: 主页：状态已配置" in output


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


def test_star_cli_stops_normally_when_wait_until_color_demo_times_out(capsys) -> None:
    """验证条件等待脚本 dry-run 默认颜色超时时正常退出。"""
    assert main(["run", "wait-until-color-demo", "--dry-run"]) == 0

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "wait 0.5s",
        "wait 0.5s",
    ]
    assert captured.err == ""


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


def test_star_cli_stops_normally_when_wait_until_image_demo_times_out(capsys) -> None:
    """验证图片等待脚本 dry-run 默认未找到时正常退出。"""
    assert main(["run", "wait-until-image-demo", "--dry-run"]) == 0

    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "wait 0.5s",
        "wait 0.5s",
    ]
    assert captured.err == ""


def test_star_cli_runs_wait_until_screen_state_demo_with_custom_dry_run_state(capsys) -> None:
    """验证状态等待脚本 dry-run 可用指定状态立即成功。"""
    assert (
        main(
            [
                "run",
                "wait-until-screen-state-demo",
                "--dry-run",
                "--dry-run-screen-state",
                "主页",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out.splitlines()
    assert output == [
        "click Point(x=100, y=200)",
    ]


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


def test_star_cli_run_passes_target_application(monkeypatch) -> None:
    """验证 run 子命令把目标应用交给本地桌面 composition。"""
    calls = []

    def fake_run(script, **kwargs):
        """记录真实运行收到的目标应用。"""
        calls.append((script.name, kwargs["target_application"]))
        return _script_run_result(0, "completed")

    monkeypatch.setattr(cli, "run_script_on_local_desktop", fake_run)

    assert main(["run", "recorded-clicks", "--target-app", "Safari"]) == 0
    assert calls == [("recorded-clicks", "Safari")]


def test_star_cli_run_rejects_target_application_in_dry_run(monkeypatch, capsys) -> None:
    """验证 run dry-run 不允许请求真实应用激活。"""
    calls = []
    monkeypatch.setattr(cli, "run_script_on_local_desktop", lambda *args, **kwargs: calls.append(True))

    assert main(["run", "recorded-clicks", "--dry-run", "--target-app", "Safari"]) == 2

    captured = capsys.readouterr()
    assert "--target-app cannot be used with --dry-run" in captured.err
    assert calls == []


def test_star_cli_run_passes_target_window_title(monkeypatch) -> None:
    """验证 run 子命令把目标窗口标题交给本地桌面 composition。"""
    calls = []

    def fake_run(script, **kwargs):
        """记录真实运行收到的目标窗口标题。"""
        calls.append(kwargs["target_window_title"])
        return _script_run_result(0, "completed")

    monkeypatch.setattr(cli, "run_script_on_local_desktop", fake_run)

    assert main(
        [
            "run",
            "recorded-clicks",
            "--target-app",
            "Safari",
            "--target-window-title",
            "视觉自动化靶场",
        ]
    ) == 0
    assert calls == ["视觉自动化靶场"]


def test_star_cli_run_rejects_target_window_without_application(monkeypatch, capsys) -> None:
    """验证 run 子命令要求窗口标题和目标应用一起使用。"""
    calls = []
    monkeypatch.setattr(cli, "run_script_on_local_desktop", lambda *args, **kwargs: calls.append(True))

    assert main(
        ["run", "recorded-clicks", "--target-window-title", "视觉自动化靶场"]
    ) == 2

    captured = capsys.readouterr()
    assert "--target-window-title requires --target-app" in captured.err
    assert calls == []


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


def test_star_cli_stops_normally_when_click_image_demo_target_is_missing(capsys) -> None:
    """验证图片目标点击 demo 未配置 dry-run 图片时正常退出。"""
    assert main(["run", "click-image-demo", "--dry-run"]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


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


@pytest.mark.parametrize("command", [
    "probe-state", "capture-screen", "diagnose-screen",
    "capture-region-diagnostics", "capture-probe-diagnostics",
    "capture-region-crops", "capture-probe-crops",
])
def test_star_cli_rejects_removed_diagnostic_commands(command, capsys) -> None:
    """已移除的诊断命令应明确报参数错误，避免残留隐式入口。"""
    with pytest.raises(SystemExit) as exc:
        main([command])
    assert exc.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


@pytest.mark.parametrize("command,names", [("run", ["demo"]), ("run-plan", ["demo", "repeat-demo"])])
def test_star_cli_rejects_removed_live_probe_dry_run_option(command, names, capsys) -> None:
    """模拟运行不再通过旧参数读取真实桌面状态。"""
    with pytest.raises(SystemExit) as exc:
        main([command, *names, "--dry-run", "--dry-run-probed-screen-state"])
    assert exc.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err
