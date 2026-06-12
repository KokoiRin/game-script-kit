"""定义脚本可编排的原子动作步骤和控制流步骤。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from game_automation.domain.conditions import Condition
from game_automation.domain.geometry import Point


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


@dataclass(frozen=True, slots=True)
class Repeat:
    times: int
    steps: tuple["Step", ...]

    def __post_init__(self) -> None:
        """校验重复次数和内部步骤都可用于执行。"""
        if self.times <= 0:
            raise ValueError("repeat times must be greater than 0")
        if len(self.steps) == 0:
            raise ValueError("repeat requires at least one step")


@dataclass(frozen=True, slots=True)
class If:
    condition: Condition
    then_steps: tuple["Step", ...]
    else_steps: tuple["Step", ...] = ()

    def __post_init__(self) -> None:
        """校验条件分支至少包含一个 then 步骤。"""
        if len(self.then_steps) == 0:
            raise ValueError("if requires at least one then step")


PrimitiveAction: TypeAlias = Click | Drag | Wait
Step: TypeAlias = PrimitiveAction | Repeat | If
