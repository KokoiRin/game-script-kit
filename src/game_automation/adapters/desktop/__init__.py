"""聚合导出桌面通用 adapter。"""

from game_automation.adapters.desktop.pixel_color import PyAutoGuiPixelColorReader
from game_automation.adapters.desktop.pointer_position import PyAutoGuiPointerPositionReader
from game_automation.adapters.desktop.terminal_keyboard import TerminalKeyStateReader

__all__ = [
    "PyAutoGuiPixelColorReader",
    "PyAutoGuiPointerPositionReader",
    "TerminalKeyStateReader",
]
