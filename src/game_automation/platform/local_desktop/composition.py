"""本机桌面平台的 use case 装配。

本 module 负责把 portable application 用例接到当前桌面平台 adapter；它是迁移
平台时优先替换的 composition 点，不解释脚本步骤。
"""

from __future__ import annotations

from game_automation.portable.application.local_control import LocalControlApplication, ScreenCapture
from game_automation.portable.application.script_run import ScriptRunResult, run_script
from game_automation.portable.domain import Point, Script
from game_automation.portable.engine.ports import (
    InputDevice,
    PixelColorReader,
    ScreenImageBatchLocator,
    ScreenImageLocator,
    ScreenStateReader,
)


def run_script_on_local_desktop(
    script: Script,
    *,
    dry_run: bool,
    dry_run_color: str = "#000000",
    dry_run_images: tuple[str, ...] = (),
    dry_run_screen_state: str = "未知",
) -> ScriptRunResult:
    """用本机桌面 adapter 运行脚本。"""
    return run_script(
        script,
        dry_run=dry_run,
        dry_run_color=dry_run_color,
        dry_run_images=dry_run_images,
        dry_run_screen_state=dry_run_screen_state,
        real_device_factory=build_real_input_device,
        real_color_reader_factory=build_real_color_reader,
        real_image_locator_factory=build_real_screen_image_locator,
        real_screen_state_reader_factory=build_real_screen_state_reader,
    )


def build_local_control_application() -> LocalControlApplication:
    """创建已接入本机桌面 adapter 的本地控制应用用例。"""
    return LocalControlApplication(
        real_device_factory=build_real_input_device,
        real_color_reader_factory=build_real_color_reader,
        real_image_locator_factory=build_real_screen_image_locator,
        real_image_batch_locator_factory=build_real_screen_image_batch_locator,
        screen_capture_factory=build_real_screen_capture,
        screen_size_factory=read_real_screen_size,
    )


def build_real_input_device() -> InputDevice:
    """延迟创建真实输入 adapter，避免导入入口模块时触发平台依赖。"""
    from game_automation.platform.macos.adapters import MacOSPointerDevice

    return MacOSPointerDevice()


def build_real_color_reader() -> PixelColorReader:
    """延迟创建真实取色 adapter，避免无颜色脚本触发截图依赖。"""
    from game_automation.platform.desktop.adapters import PyAutoGuiPixelColorReader

    return PyAutoGuiPixelColorReader()


def build_real_screen_image_locator() -> ScreenImageLocator:
    """延迟创建真实图像定位 adapter，避免普通脚本触发截图依赖。"""
    from game_automation.platform.desktop.adapters import PyAutoGuiScreenImageLocator

    return PyAutoGuiScreenImageLocator()


def build_real_screen_image_batch_locator() -> ScreenImageBatchLocator:
    """延迟创建真实批量图像定位 adapter，避免打开 UI 时触发截图权限。"""
    from game_automation.platform.desktop.adapters import PyAutoGuiScreenImageLocator

    return PyAutoGuiScreenImageLocator()


def build_real_screen_state_reader() -> ScreenStateReader:
    """创建复用本地控制状态探测能力的真实界面状态 reader。"""
    return build_local_control_application().build_screen_state_reader()


def build_real_screen_capture() -> ScreenCapture:
    """延迟创建真实截屏 adapter，避免打开 UI 时触发截图权限。"""
    from game_automation.platform.desktop.adapters import PyAutoGuiScreenCapture

    return PyAutoGuiScreenCapture().capture


def read_real_screen_size() -> Point:
    """读取当前桌面点坐标尺寸，用于诊断图坐标换算。"""
    try:
        import pyautogui
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pyautogui is required for screen size. "
            "Install dependencies with: pip install -e \".[dev]\""
        ) from exc
    size = pyautogui.size()
    return Point(int(size.width), int(size.height))
