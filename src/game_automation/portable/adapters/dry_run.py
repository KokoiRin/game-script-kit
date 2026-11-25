"""实现 dry-run adapter。

输入设备将动作写入 stdout，模拟等待把声明的时长计入任务时钟。
观察端口返回预设的颜色、图片匹配和界面状态，供运行用例在无桌面访问时执行任务。
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
        """向 stdout 输出目标坐标，供调用方核对模拟点击。"""
        print(f"click {target}")

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        """输出拖拽起点、终点和时长，拖拽时长只用于展示。"""
        print(f"drag {start} -> {end} (duration={duration_seconds}s)")

    def wait(self, duration_seconds: float) -> None:
        """输出等待时长并将其累加到模拟时钟，立即返回。"""
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
