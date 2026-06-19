"""定义脚本动作可使用的动态目标。

本 module 只表达动态目标的数据和不变量；它不执行图像匹配、不读取屏幕，
也不把目标解析成最终点击坐标。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from game_automation.portable.domain.geometry import Point, Rect
from game_automation.portable.domain.image_matching import ImageTemplate
from game_automation.portable.domain.point_aliases import ImageRef


@dataclass(frozen=True, slots=True)
class ImageTarget:
    template: ImageTemplate | ImageRef
    region: Rect | None = None
    min_confidence: float = 1.0
    offset: Point = field(default_factory=lambda: Point(0, 0))

    def __post_init__(self) -> None:
        """校验图片目标最低匹配置信度必须大于 0 且不超过 1。"""
        if not 0 < self.min_confidence <= 1:
            raise ValueError("image target min_confidence must be greater than 0 and at most 1")
