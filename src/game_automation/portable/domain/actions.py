"""定义脚本可编排的动作和控制流步骤。

本 module 只描述脚本步骤的不可变数据和字段级不变量；它不解释步骤、不读取屏幕，
也不触发输入设备。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from game_automation.portable.domain.conditions import Condition
from game_automation.portable.domain.geometry import Point
from game_automation.portable.domain.point_aliases import PointRef
from game_automation.portable.domain.targets import ImageTarget


ClickTarget: TypeAlias = Point | PointRef | ImageTarget


@dataclass(frozen=True, slots=True)
class Click:
    point: ClickTarget


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


@dataclass(frozen=True, slots=True)
class WaitUntil:
    condition: Condition
    timeout_seconds: float
    interval_seconds: float

    def __post_init__(self) -> None:
        """校验条件等待的超时和轮询间隔都必须为正数。"""
        if self.timeout_seconds <= 0:
            raise ValueError("wait until timeout_seconds must be greater than 0")
        if self.interval_seconds <= 0:
            raise ValueError("wait until interval_seconds must be greater than 0")


PrimitiveAction: TypeAlias = Click | Drag | Wait
Step: TypeAlias = PrimitiveAction | Repeat | If | WaitUntil
