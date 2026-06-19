"""定义固定点位别名和点位资源目录。

本 module 只保存点位名称、点位引用和名称解析规则；它不执行脚本、
不读取屏幕，也不创建任何平台 adapter。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from game_automation.portable.domain.geometry import Point


class UnknownPointNameError(LookupError):
    """表示脚本引用了未注册的点位名称。"""


def _validate_point_name(name: str) -> None:
    """校验点位名称必须非空。"""
    if not name.strip():
        raise ValueError("point name cannot be empty")


@dataclass(frozen=True, slots=True)
class PointRef:
    name: str

    def __post_init__(self) -> None:
        """校验点位引用名称必须非空。"""
        _validate_point_name(self.name)


@dataclass(frozen=True, slots=True)
class NamedPoint:
    name: str
    point: Point

    def __post_init__(self) -> None:
        """校验命名点位名称必须非空。"""
        _validate_point_name(self.name)


@dataclass(frozen=True, slots=True)
class TargetCatalog:
    points: tuple[NamedPoint, ...] = ()
    _point_map: Mapping[str, Point] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """建立点位名称到固定坐标的查找表。"""
        point_map = {}
        for item in self.points:
            if item.name in point_map:
                raise ValueError(f"duplicate point target: {item.name}")
            point_map[item.name] = item.point
        object.__setattr__(self, "_point_map", point_map)

    def resolve_point(self, ref: Point | PointRef) -> Point:
        """把固定点或点位引用解析成 Point。"""
        if isinstance(ref, Point):
            return ref
        try:
            return self._point_map[ref.name]
        except KeyError as exc:
            raise UnknownPointNameError(f"unknown point target: {ref.name}") from exc
