"""验证通用脚本 CLI 可以列出和按名称运行脚本。"""

from types import ModuleType

from game_automation.domain import Point
from game_automation.script_cli import main


def test_script_cli_lists_available_scripts(capsys) -> None:
    """验证 list 子命令逐行输出已注册脚本。"""
    assert main(["list"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == ["demo", "recorded-clicks"]


def test_script_cli_runs_named_script_with_dry_run(capsys) -> None:
    """验证 dry-run 可以按名称运行指定脚本并打印操作。"""
    assert main(["run", "recorded-clicks", "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "duration_seconds=3" in output
    assert "Point(x=242, y=92)" in output
    assert "Point(x=736, y=323)" in output
    assert "Point(x=741, y=400)" in output
    assert "duration_seconds=10" in output


def test_script_cli_run_defaults_to_macos(monkeypatch, capsys) -> None:
    """验证 run 子命令默认使用 macOS adapter。"""
    clicks = []
    drags = []

    class FakeMacOSPointerDevice:
        def click(self, target) -> None:
            """记录默认 macOS 分支请求的点击。"""
            clicks.append(target)

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """记录默认 macOS 分支请求的拖拽。"""
            drags.append((start, end, duration_seconds))

    fake_macos_module = ModuleType("game_automation.adapters.macos")
    fake_macos_module.MacOSPointerDevice = FakeMacOSPointerDevice
    monkeypatch.setitem(
        __import__("sys").modules,
        "game_automation.adapters.macos",
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


def test_script_cli_reports_unknown_script(capsys) -> None:
    """验证未知脚本名称会返回非零退出码并写入 stderr。"""
    assert main(["run", "missing", "--dry-run"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown script: missing" in captured.err
