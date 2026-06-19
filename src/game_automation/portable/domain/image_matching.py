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
        return self.point_at("center")

    def point_at(self, anchor: str) -> Point:
        """按 anchor 名称返回匹配区域内的点位。"""
        points = {
            "center": Point(self.rect.left + self.rect.width // 2, self.rect.top + self.rect.height // 2),
            "top_left": Point(self.rect.left, self.rect.top),
            "top_center": Point(self.rect.left + self.rect.width // 2, self.rect.top),
            "top_right": Point(self.rect.left + self.rect.width, self.rect.top),
            "left_center": Point(self.rect.left, self.rect.top + self.rect.height // 2),
            "right_center": Point(self.rect.left + self.rect.width, self.rect.top + self.rect.height // 2),
            "bottom_left": Point(self.rect.left, self.rect.top + self.rect.height),
            "bottom_center": Point(self.rect.left + self.rect.width // 2, self.rect.top + self.rect.height),
            "bottom_right": Point(self.rect.left + self.rect.width, self.rect.top + self.rect.height),
        }
        try:
            return points[anchor]
        except KeyError as exc:
            raise ValueError(f"unknown image anchor: {anchor}") from exc


@dataclass(frozen=True, slots=True)
class ImageLookupResult:
    match: ImageMatch | None

    @property
    def found(self) -> bool:
        """判断本次图片查询是否找到匹配。"""
        return self.match is not None

    @property
    def rect(self) -> Rect | None:
        """返回匹配矩形，未找到时返回 None。"""
        return None if self.match is None else self.match.rect

    @property
    def center(self) -> Point | None:
        """返回匹配中心点，未找到时返回 None。"""
        return None if self.match is None else self.match.center

    @property
    def confidence(self) -> float | None:
        """返回匹配置信度，未找到时返回 None。"""
        return None if self.match is None else self.match.confidence

    def point_at(self, anchor: str) -> Point | None:
        """返回查询结果匹配区域中的 anchor 点位，未找到时返回 None。"""
        return None if self.match is None else self.match.point_at(anchor)


@dataclass(frozen=True, slots=True)
class ImageBatchMatchResult:
    template: ImageTemplate
    match: ImageMatch | None
    elapsed_ms: float
    skipped: bool = False

    def __post_init__(self) -> None:
        """校验批量匹配中单个模板耗时必须非负。"""
        if self.elapsed_ms < 0:
            raise ValueError("image batch match elapsed_ms cannot be negative")
        if self.skipped and self.match is not None:
            raise ValueError("skipped image batch result cannot contain a match")

    @classmethod
    def skipped_result(cls, template: ImageTemplate) -> "ImageBatchMatchResult":
        """构造批量匹配中未执行的模板结果。"""
        return cls(template=template, match=None, elapsed_ms=0, skipped=True)

    @property
    def found(self) -> bool:
        """判断批量匹配中该模板是否命中。"""
        return self.match is not None

    @property
    def confidence(self) -> float | None:
        """返回该模板命中的置信度，未命中时返回 None。"""
        return None if self.match is None else self.match.confidence
