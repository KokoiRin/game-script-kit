"""定义脚本可编排的动作和控制流步骤。

本 module 只描述脚本步骤的不可变数据和字段级不变量；它不解释步骤、不读取屏幕，
也不触发输入设备。
"""

from __future__ import annotations

from dataclasses import dataclass
from string import ascii_lowercase, digits
from math import isfinite
from typing import TypeAlias

from game_automation.portable.domain.conditions import Condition
from game_automation.portable.domain.geometry import Point
from game_automation.portable.domain.point_aliases import PointRef
from game_automation.portable.domain.target_offsets import OffsetTarget
from game_automation.portable.domain.targets import ImageTarget


ClickTarget: TypeAlias = Point | PointRef | ImageTarget | OffsetTarget


@dataclass(frozen=True, slots=True)
class Click:
    point: ClickTarget
    then_hotkeys: tuple["Hotkey", ...] = ()

    def __post_init__(self) -> None:
        """校验点击后连续执行的键盘动作，不接受未经校验的原始键名。"""
        if not isinstance(self.then_hotkeys, tuple) or not all(
            isinstance(action, Hotkey) for action in self.then_hotkeys
        ):
            raise ValueError("click then_hotkeys must be a tuple of Hotkey actions")


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
    times: int | None
    steps: tuple["Step", ...]
    break_if: Condition | None = None
    max_seconds: float | None = None

    def __post_init__(self) -> None:
        """校验有限次数为正且步骤非空，None 表示无限循环。"""
        if self.times is not None and self.times <= 0:
            raise ValueError("repeat times must be greater than 0")
        if len(self.steps) == 0:
            raise ValueError("repeat requires at least one step")
        if self.max_seconds is not None and (
            type(self.max_seconds) not in (int, float)
            or not isfinite(self.max_seconds) or self.max_seconds <= 0
        ):
            raise ValueError("repeat max_seconds must be positive finite seconds")


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
    timeout_seconds: float | None
    interval_seconds: float

    def __post_init__(self) -> None:
        """校验有限超时和轮询间隔为正，None 表示等待直到满足或取消。"""
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("wait until timeout_seconds must be greater than 0")
        if self.interval_seconds <= 0:
            raise ValueError("wait until interval_seconds must be greater than 0")


@dataclass(frozen=True, slots=True)
class Hotkey:
    """表示依次按下并逆序释放的一组键，不读取或修改剪贴板。"""

    keys: tuple[str, ...]

    def __post_init__(self) -> None:
        """校验有限键集合，避免拼错键名被底层静默忽略。"""
        if not isinstance(self.keys, tuple) or not self.keys:
            raise ValueError("hotkey keys must be a non-empty tuple")
        supported = frozenset(ascii_lowercase + digits) | {
            "command", "ctrl", "alt", "shift", "enter", "tab", "esc", "space",
        }
        for key in self.keys:
            if not isinstance(key, str) or key not in supported:
                raise ValueError(f"unsupported hotkey key: {key!r}")
        if len(set(self.keys)) != len(self.keys):
            raise ValueError("hotkey keys must not contain duplicates")


PrimitiveAction: TypeAlias = Click | Drag | Wait | Hotkey
Step: TypeAlias = PrimitiveAction | Repeat | If | WaitUntil
