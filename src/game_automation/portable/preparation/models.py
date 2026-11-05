"""定义素材准备的数据边界。

本 module 只表达目标窗口和截图数据；不依赖 UI、Pillow、系统窗口或脚本执行。
"""

from dataclasses import dataclass

from game_automation.portable.domain.geometry import Rect


@dataclass(frozen=True, slots=True)
class DesktopWindow:
    """保存一次查询得到的窗口标识与逻辑屏幕范围。"""

    id: str
    application: str
    title: str
    rect: Rect


@dataclass(frozen=True, slots=True)
class ImageData:
    """通过 PNG 字节与实际像素尺寸隔离图像库对象。"""

    png: bytes
    width: int
    height: int

    def __post_init__(self) -> None:
        """拒绝没有图像内容或正向尺寸的截图。"""
        if not self.png or self.width <= 0 or self.height <= 0:
            raise ValueError("image data and dimensions must be positive")


@dataclass(frozen=True, slots=True)
class PreparedFrame:
    """把截图、窗口位置和采集时间绑定为不可变的一帧。"""

    id: str
    window: DesktopWindow
    image: ImageData
    captured_at: float
