"""定义屏幕图像匹配相关的领域值对象。

本 module 只表达模板图片和匹配结果的不变量；它不读取图片文件、不截图，
也不选择或执行具体图像匹配算法。
"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.portable.domain.geometry import Point, Rect


@dataclass(frozen=True, slots=True)
class ImageTemplate:
    path: str

    def __post_init__(self) -> None:
        """校验模板图片路径必须非空。"""
        if not self.path.strip():
            raise ValueError("image template path cannot be empty")


@dataclass(frozen=True, slots=True)
class ImageMatch:
    rect: Rect
    confidence: float

    def __post_init__(self) -> None:
        """校验匹配置信度必须落在 0 到 1 之间。"""
        if not 0 <= self.confidence <= 1:
            raise ValueError("image match confidence must be between 0 and 1")

    @property
    def center(self) -> Point:
        """计算匹配区域的中心屏幕坐标。"""
        return Point(
            x=self.rect.left + self.rect.width // 2,
            y=self.rect.top + self.rect.height // 2,
        )
