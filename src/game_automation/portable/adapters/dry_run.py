"""实现 dry-run adapter。

本 module 只把输入动作打印到 stdout，并为条件脚本提供固定屏幕状态结果；
它不执行真实输入动作、不读取真实屏幕，也不决定 dry-run 模式何时启用。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from time import monotonic

from game_automation.portable.domain import (
    Color,
    ImageMatch,
    ImageTemplate,
    Point,
    Rect,
)
from game_automation.portable.engine.ports import (
    InputDevice,
    PixelColorReader,
    RunLogger,
    ScreenImageLocator,
    ScreenStateReader,
)


class DryRunInputDevice(InputDevice):
    def __init__(self) -> None:
        """模拟等待推进虚拟时间，限时循环无需真的等待数分钟。"""
        self._started = monotonic()
        self._waited = 0.0

    def clock(self) -> float:
        """累计声明的等待和真实处理耗时，避免模拟无等待循环冻结时间。"""
        return monotonic() - self._started + self._waited

    def hotkey(self, keys: tuple[str, ...]) -> None:
        """打印组合键，不触发键盘或读取剪贴板。"""
        print(f"hotkey {'+'.join(keys)}")

    def click(self, target: Point) -> None:
        print(f"click {target}")

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        print(f"drag {start} -> {end} (duration={duration_seconds}s)")

    def wait(self, duration_seconds: float) -> None:
        print(f"wait {duration_seconds}s")
        self._waited += duration_seconds


@dataclass(frozen=True, slots=True)
class DryRunPixelColorReader(PixelColorReader):
    color: Color

    def read_color(self, point: Point) -> Color:
        """返回固定颜色，让 dry-run 条件分支可预测。"""
        return self.color


@dataclass(frozen=True, slots=True)
class DryRunScreenImageLocator(ScreenImageLocator):
    matches: Mapping[ImageTemplate, ImageMatch]

    def locate(
        self,
        template: ImageTemplate,
        *,
        region: Rect | None = None,
        min_confidence: float = 1.0,
        logger: RunLogger | None = None,
    ) -> ImageMatch | None:
        """按预设模板结果返回匹配，让 dry-run 图像定位可预测。"""
        match = self.matches.get(template)
        if match is None or match.confidence < min_confidence:
            return None
        return match


@dataclass(frozen=True, slots=True)
class DryRunScreenStateReader(ScreenStateReader):
    state: str

    def read_current_state(
        self,
        *,
        min_confidence: float = 0.8,
        logger: RunLogger | None = None,
    ) -> str:
        """返回固定界面状态，让 dry-run 状态条件可预测。"""
        return self.state
