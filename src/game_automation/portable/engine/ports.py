"""定义执行引擎需要的跨平台端口。

本 module 只声明 engine 可调用的 Protocol seam；它不包含任何平台实现，
也不决定 adapter 如何创建。
"""

from __future__ import annotations

from typing import Protocol

from game_automation.portable.domain import Color, ImageBatchMatchResult, ImageMatch, ImageTemplate, Point, Rect


class InputDevice(Protocol):
    def click(self, target: Point) -> None:
        """在屏幕坐标点执行一次跨平台点击。"""

    def drag_to(self, start: Point, end: Point, duration_seconds: float = 0.0) -> None:
        """从屏幕起点拖拽到屏幕终点。"""

    def wait(self, duration_seconds: float) -> None:
        """等待指定秒数。"""


class PointerPositionReader(Protocol):
    def current_position(self) -> Point:
        """读取当前指针的屏幕坐标。"""


class PixelColorReader(Protocol):
    def read_color(self, point: Point) -> Color:
        """读取指定屏幕坐标点的 RGB 颜色。"""
        ...


class RunLogger(Protocol):
    def log(self, message: str) -> None:
        """记录一条脚本运行诊断日志。"""
        ...


class ScreenImageLocator(Protocol):
    def locate(
        self,
        template: ImageTemplate,
        *,
        region: Rect | None = None,
        min_confidence: float = 1.0,
        logger: RunLogger | None = None,
    ) -> ImageMatch | None:
        """在当前屏幕或指定区域内查找模板图片。"""
        ...


class ScreenImageBatchLocator(Protocol):
    def locate_many(
        self,
        templates: tuple[ImageTemplate, ...],
        *,
        region: Rect | None = None,
        min_confidence: float = 1.0,
        logger: RunLogger | None = None,
    ) -> tuple[ImageBatchMatchResult, ...]:
        """在同一张屏幕截图内查找多张模板图片。"""
        ...


class CancellationToken(Protocol):
    def is_cancelled(self) -> bool:
        """返回当前脚本运行是否已被请求取消。"""
        ...


class KeyStateReader(Protocol):
    def is_pressed(self, key: str) -> bool:
        """判断指定按键是否在本轮检测中被触发。"""
