"""解析函数任务声明的目标窗口和资源元信息。

本模块将已读取的声明转换为领域值，不枚举目录、不读取源码，也不执行任务。
Python 发现阶段通过此模块校验资源路径和声明字段。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from game_automation.portable.domain import (
    ImageRef,
    ImageSearchSpec,
    ImageTemplate,
    NamedImage,
    NamedImageSearch,
    NamedPoint,
    NamedRegion,
    Point,
    Rect,
    RegionRef,
    TargetCatalog,
)
from game_automation.portable.domain.task import ScriptTarget


def parse_script_resources(value: Any, *, asset_root: Path) -> TargetCatalog:
    """解析 TASK 中的局部资源声明。"""
    if not isinstance(value, dict):
        raise ValueError("script resources must be an object")
    return TargetCatalog(
        points=_parse_points(value.get("points", {})),
        images=_parse_images(value.get("images", {}), asset_root=asset_root),
        regions=_parse_regions(value.get("regions", {})),
        searches=_parse_searches(value.get("searches", {})),
    )


def _parse_points(value: Any) -> tuple[NamedPoint, ...]:
    """解析命名点位表。"""
    if not isinstance(value, dict):
        raise ValueError("script resources points must be an object")
    return tuple(
        NamedPoint(str(name), _parse_point(point_value, field=f"point resource {name}"))
        for name, point_value in value.items()
    )


def _parse_images(value: Any, *, asset_root: Path) -> tuple[NamedImage, ...]:
    """解析命名图片表。"""
    if not isinstance(value, dict):
        raise ValueError("script resources images must be an object")
    return tuple(
        NamedImage(
            str(name),
            ImageTemplate(
                str(asset_root / _text_value(image_value, f"image resource {name}"))
            ),
        )
        for name, image_value in value.items()
    )


def _parse_regions(value: Any) -> tuple[NamedRegion, ...]:
    """解析命名区域表。"""
    if not isinstance(value, dict):
        raise ValueError("script resources regions must be an object")
    return tuple(
        NamedRegion(
            str(name), _parse_rect(region_value, field=f"region resource {name}")
        )
        for name, region_value in value.items()
    )


def _parse_searches(value: Any) -> tuple[NamedImageSearch, ...]:
    """解析命名图片搜索表。"""
    if not isinstance(value, dict):
        raise ValueError("script resources searches must be an object")
    searches = []
    for name, search_value in value.items():
        if not isinstance(search_value, dict):
            raise ValueError(f"image search resource {name} must be an object")
        searches.append(
            NamedImageSearch(
                str(name),
                ImageSearchSpec(
                    ImageRef(
                        _required_text(
                            search_value, "image", f"image search resource {name} image"
                        )
                    ),
                    region=_parse_region_ref(search_value.get("region")),
                    min_confidence=_parse_optional_confidence(
                        search_value.get("min_confidence")
                    ),
                ),
            )
        )
    return tuple(searches)


def _parse_point(value: Any, *, field: str) -> Point:
    """解析 x/y 坐标对象。"""
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return Point(
        _int_value(value.get("x"), f"{field} x"),
        _int_value(value.get("y"), f"{field} y"),
    )


def _parse_rect(value: Any, *, field: str) -> Rect:
    """解析矩形区域对象。"""
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return Rect(
        left=_int_value(value.get("left"), f"{field} left"),
        top=_int_value(value.get("top"), f"{field} top"),
        width=_int_value(value.get("width"), f"{field} width"),
        height=_int_value(value.get("height"), f"{field} height"),
    )


def _parse_region_ref(value: Any) -> RegionRef | Rect | None:
    """解析搜索区域引用或内联矩形。"""
    if value is None:
        return None
    if isinstance(value, str):
        return RegionRef(value)
    return _parse_rect(value, field="image search region")


def _parse_optional_confidence(value: Any) -> float | None:
    """解析可选置信度。"""
    if value is None:
        return None
    return _number_value(value, "min_confidence")


def _required_text(data: dict[str, Any], key: str, field: str) -> str:
    """读取必填字符串字段。"""
    if key not in data:
        raise ValueError(f"{field} is required")
    return _text_value(data[key], field)


def _text_value(value: Any, field: str) -> str:
    """解析非空字符串。"""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _number_value(value: Any, field: str) -> float:
    """解析数字字段并排除 bool。"""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be a number")
    return float(value)


def _int_value(value: Any, field: str) -> int:
    """解析整数字段并排除 bool。"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def parse_script_target(value: Any) -> ScriptTarget | None:
    """解析 TASK 中的可选目标窗口声明。"""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("script target must be an object")
    required = {"application", "window_title", "width", "height"}
    if value.keys() - (required | {"backend"}) or not required <= value.keys():
        raise ValueError(
            "script target requires application, window_title, width, height and optional backend"
        )
    return ScriptTarget(
        value["application"],
        value["window_title"],
        value["width"],
        value["height"],
        backend=value.get("backend", "desktop"),
    )
