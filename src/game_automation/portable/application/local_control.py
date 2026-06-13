"""为本地控制 UI 提供应用层用例。

本 module 收敛 UI 需要的脚本列表、命名脚本运行和固定测试任务能力；它不渲染
HTML、不解析 HTTP，也不直接解释脚本步骤或创建平台自动化 adapter。
"""

from __future__ import annotations

import io
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.script_run import (
    InputDeviceFactory,
    PixelColorReaderFactory,
    run_script,
)
from game_automation.portable.scripts_manager import DEFAULT_SCRIPT_CATALOG
from game_automation.portable.scripts_manager.catalog import ScriptCatalog, ScriptNotFoundError

CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]

PROJECT_ROOT = Path(__file__).resolve().parents[4]


@dataclass(frozen=True, slots=True)
class ControlResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""


class LocalControlApplication:
    def __init__(
        self,
        catalog: ScriptCatalog = DEFAULT_SCRIPT_CATALOG,
        *,
        command_runner: CommandRunner | None = None,
        project_root: Path = PROJECT_ROOT,
        real_device_factory: InputDeviceFactory | None = None,
        real_color_reader_factory: PixelColorReaderFactory | None = None,
    ) -> None:
        self._catalog = catalog
        self._command_runner = command_runner if command_runner is not None else _run_command
        self._project_root = project_root
        self._real_device_factory = real_device_factory
        self._real_color_reader_factory = real_color_reader_factory
        self._test_tasks: dict[str, tuple[str, ...]] = {
            "all": (sys.executable, "-m", "pytest"),
        }

    def list_scripts(self) -> tuple[str, ...]:
        """返回 UI 可展示的脚本名称列表。"""
        return self._catalog.list_names()

    def run_named_script(
        self,
        name: str,
        *,
        dry_run: bool,
        dry_run_color: str = "#000000",
    ) -> ControlResult:
        """按名称运行脚本，并捕获入口层可展示的输出。"""
        try:
            script = self._catalog.get(name)
        except ScriptNotFoundError as exc:
            return ControlResult(exit_code=1, stderr=str(exc))

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = run_script(
                script,
                dry_run=dry_run,
                dry_run_color=dry_run_color,
                real_device_factory=self._real_device_factory,
                real_color_reader_factory=self._real_color_reader_factory,
            )

        if result.error_message is not None:
            stderr.write(result.error_message)
            stderr.write("\n")
        return ControlResult(
            exit_code=result.exit_code,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def run_tests(self, task_name: str = "all") -> ControlResult:
        """运行白名单测试任务，并返回 UI 可展示的执行结果。"""
        command = self._test_tasks.get(task_name)
        if command is None:
            return ControlResult(
                exit_code=2,
                stderr=f"unknown test task: {task_name}\n",
            )

        completed = self._command_runner(command, self._project_root)
        return ControlResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def _run_command(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """执行 application 层白名单命令，不经过 shell。"""
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
