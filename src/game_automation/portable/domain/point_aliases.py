"""定义固定点位、图片搜索资源别名和脚本资源目录。

本 module 只保存资源名称、资源引用、搜索规格和名称解析规则；它不执行脚本、
不读取屏幕，也不创建任何平台 adapter。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from game_automation.portable.domain.geometry import Point, Rect
from game_automation.portable.domain.image_matching import ImageTemplate


class UnknownPointNameError(LookupError):
    """表示脚本引用了未注册的点位名称。"""


class UnknownImageNameError(LookupError):
    """表示脚本引用了未注册的图片名称。"""


class UnknownRegionNameError(LookupError):
    """表示脚本引用了未注册的区域名称。"""


class UnknownImageSearchNameError(LookupError):
    """表示脚本引用了未注册的图片搜索名称。"""


def _validate_point_name(name: str) -> None:
    """校验点位名称必须非空。"""
    if not name.strip():
        raise ValueError("point name cannot be empty")


def _validate_image_name(name: str) -> None:
    """校验图片名称必须非空。"""
    if not name.strip():
        raise ValueError("image name cannot be empty")


def _validate_region_name(name: str) -> None:
    """校验区域名称必须非空。"""
    if not name.strip():
        raise ValueError("region name cannot be empty")


def _validate_image_search_name(name: str) -> None:
    """校验图片搜索名称必须非空。"""
    if not name.strip():
        raise ValueError("image search name cannot be empty")


@dataclass(frozen=True, slots=True)
class PointRef:
    name: str

    def __post_init__(self) -> None:
        """校验点位引用名称必须非空。"""
        _validate_point_name(self.name)

    def offset(self, *, x: int = 0, y: int = 0):
        """构造基于该命名点位的偏移点击目标。"""
        from game_automation.portable.domain.target_offsets import OffsetTarget

        return OffsetTarget(self, Point(x, y))


@dataclass(frozen=True, slots=True)
class ImageRef:
    name: str

    def __post_init__(self) -> None:
        """校验图片引用名称必须非空。"""
        _validate_image_name(self.name)


@dataclass(frozen=True, slots=True)
class RegionRef:
    name: str

    def __post_init__(self) -> None:
        """校验区域引用名称必须非空。"""
        _validate_region_name(self.name)


@dataclass(frozen=True, slots=True)
class SearchRef:
    name: str

    def __post_init__(self) -> None:
        """校验图片搜索引用名称必须非空。"""
        _validate_image_search_name(self.name)


@dataclass(frozen=True, slots=True)
class NamedPoint:
    name: str
    point: Point

    def __post_init__(self) -> None:
        """校验命名点位名称必须非空。"""
        _validate_point_name(self.name)


@dataclass(frozen=True, slots=True)
class NamedImage:
    name: str
    template: ImageTemplate

    def __post_init__(self) -> None:
        """校验命名图片名称必须非空。"""
        _validate_image_name(self.name)


@dataclass(frozen=True, slots=True)
class NamedRegion:
    name: str
    region: Rect

    def __post_init__(self) -> None:
        """校验命名区域名称必须非空。"""
        _validate_region_name(self.name)


@dataclass(frozen=True, slots=True)
class ImageSearchSpec:
    image: ImageTemplate | ImageRef
    region: Rect | RegionRef | None = None
    min_confidence: float | None = None

    def __post_init__(self) -> None:
        """校验图片搜索规格的可选最低置信度。"""
        if self.min_confidence is not None and not 0 < self.min_confidence <= 1:
            raise ValueError("image search min_confidence must be greater than 0 and at most 1")


@dataclass(frozen=True, slots=True)
class NamedImageSearch:
    name: str
    search: ImageSearchSpec

    def __post_init__(self) -> None:
        """校验命名图片搜索名称必须非空。"""
        _validate_image_search_name(self.name)


@dataclass(frozen=True, slots=True)
class TargetCatalog:
    points: tuple[NamedPoint, ...] = ()
    images: tuple[NamedImage, ...] = ()
    regions: tuple[NamedRegion, ...] = ()
    searches: tuple[NamedImageSearch, ...] = ()
    _point_map: Mapping[str, Point] = field(init=False, repr=False)
    _image_map: Mapping[str, ImageTemplate] = field(init=False, repr=False)
    _region_map: Mapping[str, Rect] = field(init=False, repr=False)
    _search_map: Mapping[str, ImageSearchSpec] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """建立资源名称到资源值的查找表。"""
        point_map = {}
        for item in self.points:
            if item.name in point_map:
                raise ValueError(f"duplicate point target: {item.name}")
            point_map[item.name] = item.point
        image_map = {}
        for item in self.images:
            if item.name in image_map:
                raise ValueError(f"duplicate image target: {item.name}")
            image_map[item.name] = item.template
        region_map = {}
        for item in self.regions:
            if item.name in region_map:
                raise ValueError(f"duplicate region target: {item.name}")
            region_map[item.name] = item.region
        search_map = {}
        for item in self.searches:
            if item.name in search_map:
                raise ValueError(f"duplicate image search target: {item.name}")
            search_map[item.name] = item.search
        object.__setattr__(self, "_point_map", point_map)
        object.__setattr__(self, "_image_map", image_map)
        object.__setattr__(self, "_region_map", region_map)
        object.__setattr__(self, "_search_map", search_map)

    def resolve_point(self, ref: Point | PointRef) -> Point:
        """把固定点或点位引用解析成 Point。"""
        if isinstance(ref, Point):
            return ref
        try:
            return self._point_map[ref.name]
        except KeyError as exc:
            raise UnknownPointNameError(f"unknown point target: {ref.name}") from exc

    def resolve_image(self, ref: ImageTemplate | ImageRef) -> ImageTemplate:
        """把图片模板或图片引用解析成 ImageTemplate。"""
        if isinstance(ref, ImageTemplate):
            return ref
        try:
            return self._image_map[ref.name]
        except KeyError as exc:
            raise UnknownImageNameError(f"unknown image target: {ref.name}") from exc

    def resolve_region(self, ref: Rect | RegionRef | None) -> Rect | None:
        """把区域或区域引用解析成 Rect。"""
        if ref is None or isinstance(ref, Rect):
            return ref
        try:
            return self._region_map[ref.name]
        except KeyError as exc:
            raise UnknownRegionNameError(f"unknown region target: {ref.name}") from exc

    def resolve_search(self, ref: ImageSearchSpec | SearchRef) -> ImageSearchSpec:
        """把图片搜索规格或搜索引用解析成完整搜索规格。"""
        search = ref
        if isinstance(ref, SearchRef):
            try:
                search = self._search_map[ref.name]
            except KeyError as exc:
                raise UnknownImageSearchNameError(f"unknown image search target: {ref.name}") from exc
        return ImageSearchSpec(
            image=self.resolve_image(search.image),
            region=self.resolve_region(search.region),
            min_confidence=search.min_confidence,
        )
