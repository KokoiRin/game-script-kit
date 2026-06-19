"""聚合导出桌面通用 adapter。

本 module 只提供桌面 reader adapter 的便捷 import surface；它不执行脚本，
也不负责 CLI 或应用层错误映射。
"""

from game_automation.platform.desktop.adapters.pixel_color import PyAutoGuiPixelColorReader
from game_automation.platform.desktop.adapters.image_matching import PyAutoGuiScreenImageLocator
from game_automation.platform.desktop.adapters.pointer_position import PyAutoGuiPointerPositionReader
from game_automation.platform.desktop.adapters.screen_capture import PyAutoGuiScreenCapture
from game_automation.platform.desktop.adapters.terminal_keyboard import TerminalKeyStateReader

__all__ = [
    "PyAutoGuiPixelColorReader",
    "PyAutoGuiScreenImageLocator",
    "PyAutoGuiPointerPositionReader",
    "PyAutoGuiScreenCapture",
    "TerminalKeyStateReader",
]
