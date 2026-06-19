"""验证本地控制 UI 复用的应用层 interface。

这些测试覆盖 UI 和 CLI 之外的 application seam：脚本查找、运行结果捕获、
固定测试任务白名单。它不测试 HTTP 细节，也不直接绑定 engine 内部实现。
"""

import subprocess

from game_automation.portable.domain import ImageMatch, Point, Rect
from game_automation.portable.engine.ports import InputDevice
from game_automation.portable.application.local_control import LocalControlApplication, PROJECT_ROOT


def test_local_control_project_root_points_to_repository_root() -> None:
    """验证 UI 测试按钮在项目根目录运行 pytest。"""
    assert (PROJECT_ROOT / "pyproject.toml").is_file()
    assert (PROJECT_ROOT / "tests").is_dir()


def test_local_control_runs_named_script_and_captures_dry_run_output() -> None:
    """验证 UI 用例可以按名称 dry-run 脚本并返回可展示输出。"""
    app = LocalControlApplication()

    result = app.run_named_script(
        "conditional-color-demo",
        dry_run=True,
        dry_run_color="#102030",
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "click Point(x=100, y=200)",
        "wait 0.25s",
    ]


def test_local_control_lists_image_assets_from_project_assets_folder(tmp_path) -> None:
    """验证 UI 用例只列出图片资源目录里的支持图片文件。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "start.png").write_bytes(b"fake")
    (assets / "button.jpg").write_bytes(b"fake")
    (assets / "notes.txt").write_text("skip")

    app = LocalControlApplication(project_root=tmp_path)

    assert app.image_asset_folder_label() == "assets"
    assert app.list_image_assets() == ("button.jpg", "start.png")


def test_local_control_clicks_selected_image_asset_in_dry_run(tmp_path) -> None:
    """验证 UI 用例可把 assets 里的图片作为目标执行查找并点击脚本。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "start.png").write_bytes(b"fake")
    app = LocalControlApplication(project_root=tmp_path)

    result = app.click_image_asset("start.png", dry_run=True)

    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout == "click Point(x=0, y=0)\n"


def test_local_control_passes_min_confidence_to_image_click(tmp_path) -> None:
    """验证 UI 用例会把最低匹配置信度传给图片目标。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "start.png").write_bytes(b"fake")
    clicks = []
    confidences = []

    class FakeDevice(InputDevice):
        def click(self, target) -> None:
            """记录真实点击坐标。"""
            clicks.append(target)

        def drag_to(self, start, end, duration_seconds: float = 0.0) -> None:
            """图片点击用例不会拖拽。"""

        def wait(self, duration_seconds: float) -> None:
            """图片点击用例不会等待。"""

    class FakeImageLocator:
        def locate(self, template, *, region=None, min_confidence=1.0):
            """记录最低置信度并返回固定匹配。"""
            confidences.append(min_confidence)
            return ImageMatch(Rect(10, 20, 8, 6), confidence=0.91)

    app = LocalControlApplication(
        project_root=tmp_path,
        real_device_factory=FakeDevice,
        real_image_locator_factory=FakeImageLocator,
    )

    result = app.click_image_asset("start.png", dry_run=False, min_confidence=0.7)

    assert result.exit_code == 0
    assert result.stderr == ""
    assert confidences == [0.7]
    assert clicks == [Point(14, 23)]


def test_local_control_captures_screen_debug_screenshot(tmp_path) -> None:
    """验证 UI 用例可把真实截图保存到项目内诊断文件。"""
    captured_paths = []

    def screen_capture(path):
        captured_paths.append(path)
        path.write_bytes(b"png")

    app = LocalControlApplication(project_root=tmp_path, screen_capture_factory=lambda: screen_capture)

    result = app.capture_screen_screenshot()

    screenshot_path = tmp_path / ".star" / "debug" / "screenshots" / "latest-screen.png"
    assert result.exit_code == 0
    assert result.stderr == ""
    assert result.stdout == f"saved screenshot: {screenshot_path}\n"
    assert result.screenshot_path == str(screenshot_path)
    assert screenshot_path.read_bytes() == b"png"
    assert captured_paths == [screenshot_path]


def test_local_control_rejects_image_asset_outside_assets_folder(tmp_path) -> None:
    """验证 UI 用例拒绝通过相对路径逃逸图片资源目录。"""
    app = LocalControlApplication(project_root=tmp_path)

    result = app.click_image_asset("../secret.png", dry_run=True)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "invalid image click request:" in result.stderr


def test_local_control_rejects_invalid_image_confidence(tmp_path) -> None:
    """验证 UI 用例拒绝非法图片最低匹配置信度。"""
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "start.png").write_bytes(b"fake")
    app = LocalControlApplication(project_root=tmp_path)

    result = app.click_image_asset("start.png", dry_run=True, min_confidence=1.1)

    assert result.exit_code == 2
    assert result.stdout == ""
    assert "image target min_confidence" in result.stderr


def test_local_control_rejects_unknown_test_task_without_running_command() -> None:
    """验证 UI 只能触发白名单测试任务。"""
    commands = []

    def command_runner(command, cwd):
        commands.append((command, cwd))
        raise AssertionError("unknown test task must not execute a command")

    app = LocalControlApplication(command_runner=command_runner)

    result = app.run_tests("shell")

    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr == "unknown test task: shell\n"
    assert commands == []


def test_local_control_runs_whitelisted_test_task() -> None:
    """验证 UI 测试按钮只通过固定任务执行命令。"""
    commands = []

    def command_runner(command, cwd):
        commands.append((tuple(command), cwd))
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="2 passed\n",
            stderr="",
        )

    app = LocalControlApplication(command_runner=command_runner)

    result = app.run_tests("all")

    assert result.exit_code == 0
    assert result.stdout == "2 passed\n"
    assert result.stderr == ""
    assert len(commands) == 1
    assert commands[0][0][-2:] == ("-m", "pytest")
