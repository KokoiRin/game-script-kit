"""声明素材准备所消费的外部能力。

本 module 隔离窗口操作、截图、图像裁剪与素材存储；不要求脚本执行服务存在。
"""

from typing import Protocol

from game_automation.portable.domain.geometry import Rect
from game_automation.portable.preparation.models import DesktopWindow, ImageData


class PreparationWindows(Protocol):
    def list_windows(self, application: str) -> tuple[DesktopWindow, ...]:
        """查询指定应用可选窗口，不改变焦点。"""
        ...

    def focus_window(self, application: str, window_id: str) -> DesktopWindow:
        """重新定位并激活明确选中的窗口，返回当前范围。"""
        ...


class FrameCapture(Protocol):
    def capture(self, region: Rect) -> ImageData:
        """按逻辑屏幕范围采集 PNG 和实际像素尺寸。"""
        ...


class ImageEditor(Protocol):
    def crop(self, image: ImageData, region: Rect) -> ImageData:
        """按图像像素范围裁剪已有图片，不重新采集桌面。"""
        ...


class TemplateStore(Protocol):
    def save_png(self, name: str, png: bytes) -> str:
        """保存命名模板并返回相对 assets 的路径，禁止静默覆盖。"""
        ...
