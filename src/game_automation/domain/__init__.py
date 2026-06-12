"""聚合导出纯领域数据模型。"""

from game_automation.domain.actions import Click, Drag, PrimitiveAction, Repeat, Step, Wait
from game_automation.domain.color import Color
from game_automation.domain.geometry import Point, Rect
from game_automation.domain.script import Script
from game_automation.domain.windows import AreaWindow, ScreenWindow, Window

__all__ = [
    "AreaWindow",
    "Click",
    "Color",
    "Drag",
    "Point",
    "PrimitiveAction",
    "Rect",
    "Repeat",
    "ScreenWindow",
    "Script",
    "Step",
    "Wait",
    "Window",
]
