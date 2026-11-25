"""定义屏幕图像匹配相关的领域值对象。

本 module 只表达模板图片和匹配结果的不变量；它不读取图片文件、不截图，
也不选择或执行具体图像匹配算法。
"""

from __future__ import annotations

from dataclasses import dataclass

from game_automation.portable.domain.color_pattern import (
    ColorPattern,
    validate_point_evidence,
)
from game_automation.portable.domain.geometry import Point, Rect

_ANCHOR_GRID = {
    "center": (1, 1),
    "top_left": (0, 0),
    "top_center": (1, 0),
    "top_right": (2, 0),
    "left_center": (0, 1),
    "right_center": (2, 1),
    "bottom_left": (0, 2),
    "bottom_center": (1, 2),
    "bottom_right": (2, 2),
}


def validate_image_anchor(anchor: str) -> None:
    """校验与匹配结果共用的九种锚点名称，未知名称抛出 ValueError。"""
    if anchor not in _ANCHOR_GRID:
        raise ValueError(f"unknown image anchor: {anchor}")


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
        """按九宫格锚点计算点位，中心向下取整，右侧与底侧使用矩形边界坐标。"""
        validate_image_anchor(anchor)
        column, row = _ANCHOR_GRID[anchor]
        return Point(
            self.rect.left + self.rect.width * column // 2,
            self.rect.top + self.rect.height * row // 2,
        )


@dataclass(frozen=True, slots=True)
class ImageLookupResult:
    match: ImageMatch | None

    @property
    def found(self) -> bool:
        """由本次匹配结果推导命中标记，调用本属性沿用已有查询结果。"""
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
class ImageSearchRequest:
    template: ImageTemplate
    region: Rect | None = None
    min_confidence: float = 1.0
    priority: int = 0
    pattern: ColorPattern | None = None

    def __post_init__(self) -> None:
        """校验图片搜索请求最低置信度必须大于 0 且不超过 1。"""
        if self.pattern is not None and not isinstance(self.pattern, ColorPattern):
            raise ValueError("image search pattern must be a ColorPattern")
        if type(self.priority) is not int:
            raise ValueError("image search priority must be an integer")
        if not 0 < self.min_confidence <= 1:
            raise ValueError(
                "image search request min_confidence must be greater than 0 and at most 1"
            )


@dataclass(frozen=True, slots=True)
class ImageBatchMatchResult:
    template: ImageTemplate
    match: ImageMatch | None
    elapsed_ms: float
    skipped: bool = False
    best_confidence: float | None = None
    best_rect: Rect | None = None
    matched_points: int | None = None
    point_count: int | None = None

    def __post_init__(self) -> None:
        """校验批量匹配中单个模板耗时、跳过状态和最佳诊断信息。"""
        validate_point_evidence(
            self.point_count,
            self.matched_points,
            skipped=self.skipped,
            found=self.match is not None,
        )
        if self.elapsed_ms < 0:
            raise ValueError("image batch match elapsed_ms cannot be negative")
        if self.skipped and self.match is not None:
            raise ValueError("skipped image batch result cannot contain a match")
        if self.skipped and self.best_confidence is not None:
            raise ValueError(
                "skipped image batch result cannot contain best confidence"
            )
        if self.skipped and self.best_rect is not None:
            raise ValueError("skipped image batch result cannot contain best rect")
        if self.best_confidence is not None and not 0 <= self.best_confidence <= 1:
            raise ValueError("image batch best confidence must be between 0 and 1")
        if self.match is not None and self.best_confidence is None:
            object.__setattr__(self, "best_confidence", self.match.confidence)
        if self.match is not None and self.best_rect is None:
            object.__setattr__(self, "best_rect", self.match.rect)

    @classmethod
    def skipped_result(cls, template: ImageTemplate) -> ImageBatchMatchResult:
        """构造批量匹配中未执行的模板结果。"""
        return cls(template=template, match=None, elapsed_ms=0, skipped=True)

    @property
    def found(self) -> bool:
        """仅实际命中的模板返回真值，未命中和跳过可再通过 skipped 区分。"""
        return self.match is not None

    @property
    def confidence(self) -> float | None:
        """返回该模板命中的置信度，未命中时返回 None。"""
        return None if self.match is None else self.match.confidence
