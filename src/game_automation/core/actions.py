"""定义脚本可编排的第一版动作模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from game_automation.core.geometry import Point


@dataclass(frozen=True, slots=True)
class Click:
    point: Point


@dataclass(frozen=True, slots=True)
class Drag:
    start: Point
    end: Point
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        """校验拖拽持续时间不能为负数。"""
        if self.duration_seconds < 0:
            raise ValueError("drag duration_seconds must be greater than or equal to 0")


@dataclass(frozen=True, slots=True)
class Wait:
    duration_seconds: float

    def __post_init__(self) -> None:
        """校验等待持续时间不能为负数。"""
        if self.duration_seconds < 0:
            raise ValueError("wait duration_seconds must be greater than or equal to 0")


Action: TypeAlias = Click | Drag | Wait
