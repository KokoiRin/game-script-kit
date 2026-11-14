"""实现应用层 ApplicationActivator，通过 macOS 系统能力激活目标应用。

本 module 只负责系统命令调用、短暂稳定等待和平台错误转换；它不读取脚本、
不执行鼠标动作，也不决定何时需要激活应用。
"""

from __future__ import annotations

import platform
import subprocess
import time
from collections.abc import Callable

from game_automation.portable.application.ports import ApplicationActivator

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
Sleeper = Callable[[float], None]


class MacOSApplicationActivator(ApplicationActivator):
    """使用 macOS `open -a` 把指定应用切换到前台。"""

    def __init__(
        self,
        *,
        command_runner: CommandRunner | None = None,
        sleeper: Sleeper = time.sleep,
        stabilization_seconds: float = 0.5,
    ) -> None:
        """初始化可注入系统命令和等待函数的 macOS adapter。"""
        if command_runner is None and platform.system() != "Darwin":
            raise RuntimeError("macOS application activator requires Darwin")
        if stabilization_seconds < 0:
            raise ValueError("application stabilization seconds must be non-negative")
        self._command_runner = (
            subprocess.run if command_runner is None else command_runner
        )
        self._sleeper = sleeper
        self._stabilization_seconds = stabilization_seconds

    def activate(self, application: str) -> None:
        """按名称激活 macOS 应用并等待界面短暂稳定。"""
        normalized_application = application.strip()
        if not normalized_application:
            raise ValueError("target application must not be empty")
        command = ("/usr/bin/open", "-a", normalized_application)
        try:
            result = self._command_runner(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise _activation_error(normalized_application) from exc
        if result.returncode != 0:
            raise _activation_error(normalized_application)
        if self._stabilization_seconds > 0:
            self._sleeper(self._stabilization_seconds)


def _activation_error(application: str) -> RuntimeError:
    """构造不泄漏底层命令细节的稳定激活错误。"""
    return RuntimeError(
        f"failed to activate macOS application '{application}'. "
        "Check the application name and whether it is installed."
    )
