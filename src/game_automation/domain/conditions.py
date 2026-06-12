"""定义脚本运行时可评估的条件模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from game_automation.domain.color import Color
from game_automation.domain.geometry import Point


@dataclass(frozen=True, slots=True)
class ColorIs:
    point: Point
    expected: Color
    tolerance: int = 0

    def __post_init__(self) -> None:
        """校验颜色匹配容差必须是有效 RGB 通道差值。"""
        if not 0 <= self.tolerance <= 255:
            raise ValueError("color tolerance must be between 0 and 255")


Condition: TypeAlias = ColorIs
