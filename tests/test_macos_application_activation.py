"""验证 macOS 目标应用激活 adapter 的系统命令和错误映射。"""

from __future__ import annotations

from subprocess import CompletedProcess

import pytest

from game_automation.platform.macos.adapters import MacOSApplicationActivator


def test_macos_application_activator_runs_open_and_waits() -> None:
    """验证 adapter 使用参数化系统命令激活应用并等待稳定。"""
    calls = []
    waits = []

    def run_command(command, **kwargs):
        """记录系统命令并返回成功结果。"""
        calls.append((command, kwargs))
        return CompletedProcess(command, returncode=0, stdout="", stderr="")

    activator = MacOSApplicationActivator(
        command_runner=run_command,
        sleeper=waits.append,
        stabilization_seconds=0.25,
    )

    activator.activate("Safari")

    assert calls == [
        (
            ("/usr/bin/open", "-a", "Safari"),
            {"capture_output": True, "text": True, "check": False},
        )
    ]
    assert waits == [0.25]


def test_macos_application_activator_wraps_nonzero_result() -> None:
    """验证系统找不到应用时 adapter 返回可读错误。"""

    def run_command(command, **kwargs):
        """返回系统命令失败结果。"""
        return CompletedProcess(
            command, returncode=1, stdout="", stderr="application not found"
        )

    activator = MacOSApplicationActivator(
        command_runner=run_command, sleeper=lambda _: None
    )

    with pytest.raises(
        RuntimeError, match="failed to activate macOS application 'Missing App'"
    ):
        activator.activate("Missing App")


def test_macos_application_activator_wraps_command_error() -> None:
    """验证系统命令无法执行时 adapter 统一错误边界。"""

    def run_command(command, **kwargs):
        """模拟系统命令不可执行。"""
        raise OSError("open unavailable")

    activator = MacOSApplicationActivator(
        command_runner=run_command, sleeper=lambda _: None
    )

    with pytest.raises(
        RuntimeError, match="failed to activate macOS application 'Safari'"
    ):
        activator.activate("Safari")
