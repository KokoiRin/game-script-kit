"""实现坐标和颜色记录工具的核心循环。

本 module 只编排 pointer/key/color readers 来辅助人工记录坐标；它不执行命名脚本，
也不负责 CLI adapter 的创建。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from game_automation.portable.domain import Color, Point
from game_automation.portable.engine.ports import KeyStateReader, PixelColorReader, PointerPositionReader

Sleeper = Callable[[float], None]
Clock = Callable[[], float]
Output = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class RecordedPoint:
    point: Point
    color: Color


@dataclass(slots=True)
class CoordinateRecorder:
    pointer_reader: PointerPositionReader
    key_reader: KeyStateReader
    color_reader: PixelColorReader
    sleeper: Sleeper = time.sleep
    clock: Clock = time.monotonic
    output: Output = print
    display_interval_seconds: float = 1.0
    poll_interval_seconds: float = 0.05
    recorded: list[RecordedPoint] = field(default_factory=list)

    def __post_init__(self) -> None:
        """校验两个轮询节奏必须为正数。"""
        if self.display_interval_seconds <= 0:
            raise ValueError("display_interval_seconds must be greater than 0")
        if self.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be greater than 0")

    def run(self) -> tuple[RecordedPoint, ...]:
        """运行坐标和颜色记录循环，并返回本次记录。"""
        was_record_pressed = False
        next_display_at = self.clock()

        while True:
            now = self.clock()
            if now >= next_display_at:
                self._print_current_position()
                next_display_at = now + self.display_interval_seconds

            record_pressed = self.key_reader.is_pressed("1")
            if record_pressed and not was_record_pressed:
                self._record_current_position()
            was_record_pressed = record_pressed

            if self._should_stop():
                break

            # 显示和按键检查节奏分离：这里按更短的按键检测间隔休眠。
            self.sleeper(self.poll_interval_seconds)

        self._print_recorded_positions()
        return tuple(self.recorded)

    def _read_current_record(self) -> RecordedPoint:
        """读取当前鼠标坐标，并同步读取该坐标点颜色。"""
        point = self.pointer_reader.current_position()
        color = self.color_reader.read_color(point)
        return RecordedPoint(point=point, color=color)

    def _print_current_position(self) -> None:
        """读取并打印当前鼠标坐标和颜色。"""
        record = self._read_current_record()
        self.output(f"current: {record.point} {record.color}")

    def _record_current_position(self) -> None:
        """在按键边沿触发时重新读取坐标和颜色并记录。"""
        record = self._read_current_record()
        self.recorded.append(record)
        self.output(f"recorded: {record.point} {record.color}")

    def _should_stop(self) -> bool:
        """检查用户是否请求结束工具。"""
        return self.key_reader.is_pressed("q") or self.key_reader.is_pressed("Q")

    def _print_recorded_positions(self) -> None:
        """打印本次运行记录到的所有坐标和颜色。"""
        self.output("recorded points:")
        if not self.recorded:
            self.output("(none)")
            return
        for index, record in enumerate(self.recorded, start=1):
            self.output(f"{index}. {record.point} {record.color}")
