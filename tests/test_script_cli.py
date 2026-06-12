"""验证 star CLI 可以列出和按名称运行脚本。"""

from types import ModuleType

from game_automation.domain import Color, Point
from game_automation.engine.ports import InputDevice
from game_automation.star_cli import main


def test_star_cli_lists_available_scripts(capsys) -> None:
    """验证 list 子命令逐行输出已注册脚本。"""
    assert main(["list"]) == 0

    output = capsys.readouterr().out.splitlines()
    assert output == ["demo", "recorded-clicks", "repeat-demo", "conditional-color-demo"]


def test_star_cli_runs_named_script_with_dry_run(capsys) -> None:
    """验证 dry-run 可以按名称运行指定脚本并打印操作。"""
    assert main(["run", "recorded-clicks", "--dry-run"]) == 0

    output = capsys.readouterr().out
    assert "wait 3s" in output
    assert "Point(x=242, y=92)" in output
    assert "Point(x=736, y=323)" in output
    assert "Point(x=741, y=400)" in output
    assert "wait 10s" in output


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


def test_star_cli_reports_invalid_dry_run_color(capsys) -> None:
    """验证非法 dry-run 颜色会作为运行配置错误报告。"""
    assert main(["run", "conditional-color-demo", "--dry-run", "--dry-run-color", "bad"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "script run configuration failed: color must match" in captured.err


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


def test_star_cli_run_injects_color_reader_for_conditional_script(monkeypatch, capsys) -> None:
    """验证真实运行条件分支脚本时 CLI 会注入取色 adapter。"""
    import game_automation.adapters.desktop as desktop

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

    fake_macos_module = ModuleType("game_automation.adapters.macos")
    fake_macos_module.MacOSPointerDevice = FakeMacOSPointerDevice
    monkeypatch.setitem(
        __import__("sys").modules,
        "game_automation.adapters.macos",
        fake_macos_module,
    )
    monkeypatch.setattr(desktop, "PyAutoGuiPixelColorReader", FakePixelColorReader)
    monkeypatch.setitem(__import__("sys").modules, "game_automation.adapters.desktop", desktop)

    assert main(["run", "conditional-color-demo"]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert read_points == [Point(50, 60)]
    assert clicks == [Point(100, 200)]


def test_star_cli_run_reports_color_reader_setup_error(monkeypatch, capsys) -> None:
    """验证真实运行条件分支脚本时取色 adapter setup 失败会被报告。"""
    import game_automation.adapters.desktop as desktop

    class FailingPixelColorReader:
        def __init__(self) -> None:
            """模拟取色 adapter 初始化失败。"""
            raise RuntimeError("screen color unavailable")

    monkeypatch.setattr(desktop, "PyAutoGuiPixelColorReader", FailingPixelColorReader)
    monkeypatch.setitem(__import__("sys").modules, "game_automation.adapters.desktop", desktop)

    assert main(["run", "conditional-color-demo"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "script run setup failed: screen color unavailable" in captured.err


def test_star_cli_reports_unknown_script(capsys) -> None:
    """验证未知脚本名称会返回非零退出码并写入 stderr。"""
    assert main(["run", "missing", "--dry-run"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unknown script: missing" in captured.err


def test_star_cli_recorder_injects_color_reader(monkeypatch) -> None:
    """验证 recorder 子命令会组装坐标、按键和取色 adapter。"""
    import game_automation.adapters.desktop as desktop
    import game_automation.star_cli as star_cli
    import game_automation.tools.coordinate_recorder as recorder_module

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
    monkeypatch.setitem(__import__("sys").modules, "game_automation.adapters.desktop", desktop)
    monkeypatch.setitem(
        __import__("sys").modules,
        "game_automation.tools.coordinate_recorder",
        recorder_module,
    )

    assert star_cli.main(["recorder"]) == 0

    pointer_reader, key_reader, color_reader, kwargs = created["recorder_args"]
    assert pointer_reader is created["pointer"]
    assert key_reader is created["key"]
    assert color_reader is created["color"]
    assert kwargs["display_interval_seconds"] == 1.0
    assert kwargs["poll_interval_seconds"] == 0.05
    assert created["key"].closed is True


def test_star_cli_recorder_reports_color_reader_setup_error(monkeypatch, capsys) -> None:
    """验证取色 adapter 初始化失败时 CLI 返回 setup 错误。"""
    import game_automation.adapters.desktop as desktop
    import game_automation.star_cli as star_cli

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
    monkeypatch.setitem(__import__("sys").modules, "game_automation.adapters.desktop", desktop)

    assert star_cli.main(["recorder"]) == 1

    captured = capsys.readouterr()
    assert "coordinate recorder setup failed: screen color unavailable" in captured.err
