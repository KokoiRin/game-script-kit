"""聚合导出纯领域数据模型。"""

from game_automation.domain.actions import Click, Drag, If, PrimitiveAction, Repeat, Step, Wait
from game_automation.domain.color import Color
from game_automation.domain.conditions import ColorIs, Condition
from game_automation.domain.geometry import Point, Rect
from game_automation.domain.script import Script
from game_automation.domain.windows import AreaWindow, ScreenWindow, Window

__all__ = [
    "AreaWindow",
    "Click",
    "Color",
    "ColorIs",
    "Condition",
    "Drag",
    "If",
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
