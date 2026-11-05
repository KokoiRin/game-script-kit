"""编排选窗、冻结截图、取点和模板保存。

本 module 拥有一个有界冻结帧会话并统一坐标转换；不读取脚本、不执行步骤、
不依赖网页或平台库。UI、CLI 或 Agent 可直接调用相同接口。
"""

import threading
import time
from uuid import uuid4

from game_automation.portable.domain.geometry import Point, Rect
from game_automation.portable.preparation.models import DesktopWindow, PreparedFrame
from game_automation.portable.preparation.ports import FrameCapture, ImageEditor, PreparationWindows, TemplateStore


class PreparationService:
    def __init__(
        self, *, windows: PreparationWindows, capture: FrameCapture,
        images: ImageEditor, templates: TemplateStore,
    ) -> None:
        """注入准备端口，创建服务时不访问任何设备或脚本。"""
        self._windows = windows
        self._capture = capture
        self._images = images
        self._templates = templates
        self._lock = threading.Lock()
        self._frame: PreparedFrame | None = None

    def list_windows(self, application: str) -> tuple[DesktopWindow, ...]:
        """查询应用窗口，供交互层选择明确的目标。"""
        if not application.strip():
            raise ValueError("application must not be empty")
        return self._windows.list_windows(application.strip())

    def capture_window(self, application: str, window_id: str) -> PreparedFrame:
        """激活目标并获取一帧，新捕获请求立即使旧帧失效。"""
        if not application.strip() or not window_id.strip():
            raise ValueError("application and window id are required")
        with self._lock:
            self._frame = None
            window = self._windows.focus_window(application.strip(), window_id)
            image = self._capture.capture(window.rect)
            self._frame = PreparedFrame(uuid4().hex, window, image, time.time())
            return self._frame

    def locate_point(self, frame_id: str, pixel: Point) -> tuple[Point, Point]:
        """把冻结图像中的像素点转换为窗口相对坐标和屏幕坐标。"""
        with self._lock:
            frame = self._require_frame(frame_id)
            if not (0 <= pixel.x < frame.image.width and 0 <= pixel.y < frame.image.height):
                raise ValueError("point is outside the captured image")
            relative = Point(
                pixel.x * frame.window.rect.width // frame.image.width,
                pixel.y * frame.window.rect.height // frame.image.height,
            )
            return relative, relative.offset(x=frame.window.rect.left, y=frame.window.rect.top)

    def save_crop(self, frame_id: str, region: Rect, name: str) -> str:
        """从指定冻结帧裁图并保存，校验完成前不写模板。"""
        with self._lock:
            frame = self._require_frame(frame_id)
            if (region.left < 0 or region.top < 0
                    or region.left + region.width > frame.image.width
                    or region.top + region.height > frame.image.height):
                raise ValueError("crop region is outside the captured image")
            crop = self._images.crop(frame.image, region)
            return self._templates.save_png(name, crop.png)

    def _require_frame(self, frame_id: str) -> PreparedFrame:
        """只接受当前帧标识，防止其他页面或旧框选误用新截图。"""
        if self._frame is None or self._frame.id != frame_id:
            raise LookupError("frame is unavailable or replaced; capture again")
        return self._frame
