"""编排单次脚本运行的应用 module。

本 module 负责选择 dry-run 或真实 adapter、补齐脚本所需端口、调用 runner，
并把运行配置、setup 和超时错误归一化；它不做脚本注册表查找，也不打印 CLI 输出。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from game_automation.portable.adapters.dry_run import DryRunInputDevice, DryRunPixelColorReader
from game_automation.portable.domain import Color, Script
from game_automation.portable.engine.ports import InputDevice, PixelColorReader
from game_automation.portable.engine.runner import ScriptRunner
from game_automation.portable.engine.script_requirements import inspect_script_requirements

InputDeviceFactory = Callable[[], InputDevice]
PixelColorReaderFactory = Callable[[], PixelColorReader]


@dataclass(frozen=True, slots=True)
class ScriptRunResult:
    exit_code: int
    error_message: str | None = None


def run_script(
    script: Script,
    *,
    dry_run: bool,
    dry_run_color: str = "#000000",
    real_device_factory: InputDeviceFactory | None = None,
    real_color_reader_factory: PixelColorReaderFactory | None = None,
) -> ScriptRunResult:
    """运行一份已解析脚本，并返回入口层可直接映射的结果。"""
    try:
        runner = _build_runner(
            script,
            dry_run=dry_run,
            dry_run_color=dry_run_color,
            real_device_factory=real_device_factory,
            real_color_reader_factory=real_color_reader_factory,
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
    real_device_factory: InputDeviceFactory | None,
    real_color_reader_factory: PixelColorReaderFactory | None,
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
        device=_build_real_device(real_device_factory),
        color_reader=_build_real_color_reader(
            needs_color_reader=requirements.needs_color_reader,
            real_color_reader_factory=real_color_reader_factory,
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


def _build_real_device(real_device_factory: InputDeviceFactory | None) -> InputDevice:
    """通过平台层注入的工厂创建真实输入 adapter。"""
    if real_device_factory is None:
        raise RuntimeError("real input device factory is required")
    return real_device_factory()


def _build_real_color_reader(
    *,
    needs_color_reader: bool,
    real_color_reader_factory: PixelColorReaderFactory | None,
) -> PixelColorReader | None:
    """按脚本需求通过平台层注入的工厂创建真实取色 adapter。"""
    if not needs_color_reader:
        return None
    if real_color_reader_factory is None:
        raise RuntimeError("real color reader factory is required")
    return real_color_reader_factory()
