"""本机桌面平台的 use case 装配。

本 module 负责把 portable application 用例接到当前桌面平台 adapter；它是迁移
平台时优先替换的 composition 点，不解释脚本步骤。
"""

from __future__ import annotations

from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.application.script_run import ScriptRunResult, run_script
from game_automation.portable.domain import Script
from game_automation.portable.engine.ports import InputDevice, PixelColorReader


def run_script_on_local_desktop(
    script: Script,
    *,
    dry_run: bool,
    dry_run_color: str = "#000000",
) -> ScriptRunResult:
    """用本机桌面 adapter 运行脚本。"""
    return run_script(
        script,
        dry_run=dry_run,
        dry_run_color=dry_run_color,
        real_device_factory=build_real_input_device,
        real_color_reader_factory=build_real_color_reader,
    )


def build_local_control_application() -> LocalControlApplication:
    """创建已接入本机桌面 adapter 的本地控制应用用例。"""
    return LocalControlApplication(
        real_device_factory=build_real_input_device,
        real_color_reader_factory=build_real_color_reader,
    )


def build_real_input_device() -> InputDevice:
    """延迟创建真实输入 adapter，避免导入入口模块时触发平台依赖。"""
    from game_automation.platform.macos.adapters import MacOSPointerDevice

    return MacOSPointerDevice()


def build_real_color_reader() -> PixelColorReader:
    """延迟创建真实取色 adapter，避免无颜色脚本触发截图依赖。"""
    from game_automation.platform.desktop.adapters import PyAutoGuiPixelColorReader

    return PyAutoGuiPixelColorReader()
