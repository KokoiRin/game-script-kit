"""编排单次脚本运行的应用 module。

本 module 负责选择 dry-run 或真实 adapter、补齐脚本所需端口、调用 runner，
并把运行配置、setup 和超时错误归一化；它不做脚本注册表查找，也不打印 CLI 输出。
"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.adapters.dry_run import DryRunInputDevice, DryRunPixelColorReader
from game_automation.domain import Color, Script
from game_automation.engine.ports import InputDevice, PixelColorReader
from game_automation.engine.runner import ScriptRunner
from game_automation.engine.script_requirements import inspect_script_requirements


@dataclass(frozen=True, slots=True)
class ScriptRunResult:
    exit_code: int
    error_message: str | None = None


def run_script(
    script: Script,
    *,
    dry_run: bool,
    dry_run_color: str = "#000000",
) -> ScriptRunResult:
    """运行一份已解析脚本，并返回入口层可直接映射的结果。"""
    try:
        runner = _build_runner(
            script,
            dry_run=dry_run,
            dry_run_color=dry_run_color,
        )
    except ValueError as exc:
        return ScriptRunResult(
            exit_code=2,
            error_message=f"script run configuration failed: {exc}",
        )
    except RuntimeError as exc:
        return ScriptRunResult(
            exit_code=1,
            error_message=f"script run setup failed: {exc}",
        )

    try:
        runner.run(script)
    except TimeoutError as exc:
        return ScriptRunResult(
            exit_code=1,
            error_message=f"script run timed out: {exc}",
        )
    return ScriptRunResult(exit_code=0)


def _build_runner(
    script: Script,
    *,
    dry_run: bool,
    dry_run_color: str,
) -> ScriptRunner:
    """按脚本运行模式和端口需求组装 runner。"""
    requirements = inspect_script_requirements(script)
    if dry_run:
        return ScriptRunner(
            device=DryRunInputDevice(),
            color_reader=_build_dry_run_color_reader(
                dry_run_color,
                needs_color_reader=requirements.needs_color_reader,
            ),
        )

    return ScriptRunner(
        device=_build_macos_device(),
        color_reader=_build_desktop_color_reader(
            needs_color_reader=requirements.needs_color_reader,
        ),
    )


def _build_dry_run_color_reader(
    dry_run_color: str,
    *,
    needs_color_reader: bool,
) -> PixelColorReader | None:
    """按脚本需求创建 dry-run 固定取色 adapter。"""
    if not needs_color_reader:
        return None
    return DryRunPixelColorReader(Color.from_hex(dry_run_color))


def _build_macos_device() -> InputDevice:
    """延迟创建真实输入 adapter，避免导入 CLI 时触发平台依赖。"""
    from game_automation.adapters.macos import MacOSPointerDevice

    return MacOSPointerDevice()


def _build_desktop_color_reader(*, needs_color_reader: bool) -> PixelColorReader | None:
    """按脚本需求延迟创建真实取色 adapter。"""
    if not needs_color_reader:
        return None

    from game_automation.adapters.desktop import PyAutoGuiPixelColorReader

    return PyAutoGuiPixelColorReader()
