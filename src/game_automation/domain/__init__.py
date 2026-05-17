"""聚合导出纯领域数据模型。"""

from game_automation.domain.actions import Action, Click, Drag, Wait
from game_automation.domain.geometry import Point, Rect
from game_automation.domain.script import Script
from game_automation.domain.windows import AreaWindow, ScreenWindow, Window

__all__ = [
    "Action",
    "AreaWindow",
    "Click",
    "Drag",
    "Point",
    "Rect",
    "ScreenWindow",
    "Script",
    "Wait",
    "Window",
]
