"""实现素材准备的截图、图像编辑与工作区模板存储端口。

本 module 复用公共截图坐标转换并封装 Pillow；不调用脚本、状态机或 UI。
"""

import io
from pathlib import Path
import re

from PIL import Image

from game_automation.platform.desktop.adapters.screen_capture import capture_screen, crop_captured_screen
from game_automation.portable.domain.geometry import Rect
from game_automation.portable.preparation.models import ImageData


def _encode(image: Image.Image) -> ImageData:
    """把库内图像转换为跨层传递的 PNG 值对象。"""
    output = io.BytesIO()
    image.save(output, format="PNG")
    return ImageData(output.getvalue(), image.width, image.height)


class DesktopFrameCapture:
    def __init__(self, backend: object | None = None) -> None:
        """保存可选截图 backend，不在构造时读取桌面。"""
        self._backend = backend

    def capture(self, region: Rect) -> ImageData:
        """截取窗口范围，拒绝超出当前主屏幕的区域。"""
        try:
            if self._backend is None:
                import pyautogui
                self._backend = pyautogui
            screen = capture_screen(self._backend)
            if (region.left < 0 or region.top < 0
                    or (region.left + region.width) * screen.pixels_per_point_x > screen.image.width
                    or (region.top + region.height) * screen.pixels_per_point_y > screen.image.height):
                raise RuntimeError("window is outside the captured primary display")
            return _encode(crop_captured_screen(screen, region=region).image)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("window capture failed; check Screen Recording permission and desktop session") from exc


class PillowImageEditor:
    def crop(self, image: ImageData, region: Rect) -> ImageData:
        """仅裁剪传入 PNG 内容，不重新截图。"""
        with Image.open(io.BytesIO(image.png)) as decoded:
            return _encode(decoded.crop((region.left, region.top,
                                         region.left + region.width, region.top + region.height)))


class WorkspaceTemplateStore:
    def __init__(self, workspace: Path) -> None:
        """绑定唯一素材工作区，不扫描或加载脚本。"""
        self._workspace = workspace.resolve()

    def save_png(self, name: str, png: bytes) -> str:
        """将命名 PNG 排他写入 assets，拒绝路径和同名覆盖。"""
        if not re.fullmatch(r"[\w -]{1,80}", name):
            raise ValueError("template name must contain 1-80 letters, numbers, spaces, underscores or hyphens")
        root = (self._workspace / "assets").resolve()
        if not root.is_relative_to(self._workspace):
            raise ValueError("template assets must stay inside workspace")
        root.mkdir(parents=True, exist_ok=True)
        filename = f"{name}.png"
        with (root / filename).open("xb") as output:
            output.write(png)
        return filename
