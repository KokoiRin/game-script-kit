"""定义脚本运行时可评估的条件模型。

本 module 只保存条件表达式及其不变量；它不评估条件、不读取屏幕，
也不决定条件满足后执行哪个分支。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from game_automation.portable.domain.color import Color
from game_automation.portable.domain.geometry import Point, Rect
from game_automation.portable.domain.image_matching import ImageTemplate
from game_automation.portable.domain.point_aliases import ImageRef, ImageSearchSpec, SearchRef


@dataclass(frozen=True, slots=True)
class ColorIs:
    point: Point
    expected: Color
    tolerance: int = 0

    def __post_init__(self) -> None:
        """校验颜色匹配容差必须是有效 RGB 通道差值。"""
        if not 0 <= self.tolerance <= 255:
            raise ValueError("color tolerance must be between 0 and 255")


@dataclass(frozen=True, slots=True)
class ImageExists:
    template: ImageTemplate | ImageRef | ImageSearchSpec | SearchRef
    region: Rect | None = None
    min_confidence: float | None = None

    def __post_init__(self) -> None:
        """校验图片匹配最低置信度必须大于 0 且不超过 1。"""
        if self.min_confidence is not None and not 0 < self.min_confidence <= 1:
            raise ValueError("image exists min_confidence must be greater than 0 and at most 1")


@dataclass(frozen=True, slots=True)
class ScreenStateIs:
    state: str
    min_confidence: float = 0.8

    def __post_init__(self) -> None:
        """校验界面状态名称和最低识别置信度。"""
        if not self.state.strip():
            raise ValueError("screen state condition state cannot be empty")
        if not 0 < self.min_confidence <= 1:
            raise ValueError("screen state condition min_confidence must be greater than 0 and at most 1")


Condition: TypeAlias = ColorIs | ImageExists | ScreenStateIs
