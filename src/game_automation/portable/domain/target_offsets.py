"""定义点击目标的通用点位偏移包装。

本 module 只表达“先解析基础目标，再应用 offset”的纯领域数据；它不解析名称、
不查找图片，也不调用任何平台 adapter。
"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.portable.domain.geometry import Point
from game_automation.portable.domain.point_aliases import PointRef
from game_automation.portable.domain.targets import ImageTarget


@dataclass(frozen=True, slots=True)
class OffsetTarget:
    base: Point | PointRef | ImageTarget
    offset: Point

    def offset_by(self, *, x: int = 0, y: int = 0) -> "OffsetTarget":
        """返回累计偏移后的新偏移目标。"""
        return OffsetTarget(self.base, self.offset.offset(x=x, y=y))
