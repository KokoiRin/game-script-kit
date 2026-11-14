"""验证原生启动器边界与退出转发，不要求当前机器具有 macOS SDK。

本 module 替换平台与子进程边界，检查启动参数和失败提示，不模拟 SwiftUI 编译。
"""

import signal
import sys

import pytest

from game_automation.platform.local_desktop.entrypoints import desktop_app


def test_native_launcher_reports_unsupported_platform(monkeypatch):
    """Linux 不应尝试启动网页或 Qt 作为隐式降级。"""
    monkeypatch.setattr(desktop_app.platform, "system", lambda: "Linux")
    with pytest.raises(RuntimeError, match="macOS"):
        desktop_app.launch_desktop()


def test_native_launcher_passes_workspace_and_current_python(tmp_path, monkeypatch):
    """原生壳使用当前虚拟环境，并以独立会话启动。"""
    executable = tmp_path / "native/StarDesktop/.build/debug/StarDesktop"
    executable.parent.mkdir(parents=True)
    executable.write_text("native binary")
    executable.chmod(0o755)
    monkeypatch.setenv("STAR_SOURCE_ROOT", str(tmp_path))
    monkeypatch.delenv("STAR_DESKTOP_EXECUTABLE", raising=False)
    monkeypatch.setattr(desktop_app.platform, "system", lambda: "Darwin")
    captured = {}

    class Child:
        def wait(self):
            """模拟用户正常关闭桌面窗口。"""
            return 0

    def launch(command, **kwargs):
        """记录结构化进程参数，不实际执行二进制。"""
        captured.update(command=command, **kwargs)
        return Child()

    monkeypatch.setattr(desktop_app.subprocess, "Popen", launch)
    assert desktop_app.launch_desktop(workspace=tmp_path) == 0
    assert captured["command"] == [
        str(executable),
        "--tab",
        "prepare",
        "--workspace",
        str(tmp_path),
    ]
    assert captured["env"]["STAR_PYTHON"] == sys.executable
    assert captured["start_new_session"] is True


def test_native_launcher_interrupt_requests_graceful_termination(tmp_path, monkeypatch):
    """终端中断先给原生壳机会回收后台，不立即遗留执行进程。"""
    executable = tmp_path / "StarDesktop"
    executable.write_text("native binary")
    executable.chmod(0o755)
    monkeypatch.setenv("STAR_DESKTOP_EXECUTABLE", str(executable))
    monkeypatch.setattr(desktop_app.platform, "system", lambda: "Darwin")
    calls = []

    class Child:
        def wait(self, timeout=None):
            """首次模拟中断，第二次模拟原生应用有序退出。"""
            calls.append(("wait", timeout))
            if timeout is None:
                raise KeyboardInterrupt
            return 0

        def send_signal(self, signum):
            """记录退出请求。"""
            calls.append(("signal", signum))

    monkeypatch.setattr(
        desktop_app.subprocess, "Popen", lambda *args, **kwargs: Child()
    )
    assert desktop_app.launch_desktop(workspace=tmp_path) == 0
    assert calls == [("wait", None), ("signal", signal.SIGTERM), ("wait", 12)]
