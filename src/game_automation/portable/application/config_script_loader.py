"""读取用户可编辑的 JSON 配置脚本。

本 module 负责把项目 `scripts/*.json` 转换成标准 Script 和 TargetCatalog；
它不执行脚本、不解析 CLI/UI 请求，也不创建真实平台 adapter。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from game_automation.portable.domain import (
    Click,
    If,
    ImageRef,
    ImageSearchSpec,
    ImageTarget,
    ImageTemplate,
    NamedImage,
    NamedImageSearch,
    NamedPoint,
    NamedRegion,
    Point,
    PointRef,
    Rect,
    RegionRef,
    Repeat,
    ScreenStateIs,
    ScreenWindow,
    Script,
    SearchRef,
    TargetCatalog,
    Wait,
    WaitUntil,
)
from game_automation.portable.domain.actions import Step


@dataclass(frozen=True, slots=True)
class ScriptConfigError:
    file: str
    message: str


@dataclass(frozen=True, slots=True)
class ConfigScriptEntry:
    file: str
    script: Script


@dataclass(frozen=True, slots=True)
class ConfigScriptLoadResult:
    entries: tuple[ConfigScriptEntry, ...] = ()
    errors: tuple[ScriptConfigError, ...] = ()


def load_config_scripts(script_dir: Path, *, asset_root: Path) -> tuple[Script, ...]:
    """读取目录中的 JSON 脚本文件，目录不存在时返回空集合。"""
    if not script_dir.exists():
        return ()
    if not script_dir.is_dir():
        raise ValueError(f"script path is not a directory: {script_dir}")
    return tuple(_load_config_script(path, asset_root=asset_root) for path in sorted(script_dir.glob("*.json")))


def load_config_scripts_with_errors(script_dir: Path, *, asset_root: Path) -> ConfigScriptLoadResult:
    """读取 JSON 脚本文件，隔离单文件错误并返回可用脚本。"""
    if not script_dir.exists():
        return ConfigScriptLoadResult()
    if not script_dir.is_dir():
        return ConfigScriptLoadResult(
            errors=(ScriptConfigError(script_dir.name, f"script path is not a directory: {script_dir}"),)
        )
    entries: list[ConfigScriptEntry] = []
    errors: list[ScriptConfigError] = []
    for path in sorted(script_dir.glob("*.json")):
        try:
            entries.append(ConfigScriptEntry(path.name, _load_config_script(path, asset_root=asset_root)))
        except ValueError as exc:
            errors.append(ScriptConfigError(path.name, str(exc)))
    return ConfigScriptLoadResult(entries=tuple(entries), errors=tuple(errors))


def _load_config_script(path: Path, *, asset_root: Path) -> Script:
    """读取单个 JSON 脚本文件，并为错误补充文件名。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _parse_config_script(data, path=path, asset_root=asset_root)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name}: invalid script json: {exc.msg}") from exc
    except (LookupError, TypeError, ValueError) as exc:
        if str(exc).startswith(f"{path.name}:"):
            raise
        raise ValueError(f"{path.name}: {exc}") from exc


def _parse_config_script(data: Any, *, path: Path, asset_root: Path) -> Script:
    """把 JSON object 转换成标准 Script。"""
    if not isinstance(data, dict):
        raise ValueError("script config must be an object")
    return Script(
        name=_required_text(data, "name", "script name"),
        window=ScreenWindow(),
        steps=_parse_steps(data.get("steps")),
        resources=_parse_resources(data.get("resources", {}), asset_root=asset_root),
    )


def _parse_resources(value: Any, *, asset_root: Path) -> TargetCatalog:
    """解析脚本文件中的局部资源别名。"""
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
        NamedImage(str(name), ImageTemplate(str(asset_root / _text_value(image_value, f"image resource {name}"))))
        for name, image_value in value.items()
    )


def _parse_regions(value: Any) -> tuple[NamedRegion, ...]:
    """解析命名区域表。"""
    if not isinstance(value, dict):
        raise ValueError("script resources regions must be an object")
    return tuple(
        NamedRegion(str(name), _parse_rect(region_value, field=f"region resource {name}"))
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
                    ImageRef(_required_text(search_value, "image", f"image search resource {name} image")),
                    region=_parse_region_ref(search_value.get("region")),
                    min_confidence=_parse_optional_confidence(search_value.get("min_confidence")),
                ),
            )
        )
    return tuple(searches)


def _parse_steps(value: Any) -> tuple[Step, ...]:
    """解析步骤列表。"""
    if not isinstance(value, list) or not value:
        raise ValueError("script steps must be a non-empty list")
    return tuple(_parse_step(item) for item in value)


def _parse_step(value: Any) -> Step:
    """解析单个步骤对象。"""
    if not isinstance(value, dict) or len(value) != 1:
        raise ValueError("script step must be an object with exactly one step type")
    step_type, payload = next(iter(value.items()))
    if step_type == "wait":
        return Wait(_number_value(payload, "wait duration"))
    if step_type == "click":
        return Click(_parse_click_target(payload))
    if step_type == "repeat":
        return _parse_repeat(payload)
    if step_type == "if_state":
        return _parse_if_state(payload)
    if step_type == "wait_until_state":
        return _parse_wait_until_state(payload)
    raise ValueError(f"unsupported step type: {step_type}")


def _parse_click_target(value: Any):
    """解析点击目标，支持点位、图片和搜索别名。"""
    if not isinstance(value, dict):
        raise ValueError("click target must be an object")
    offset = _parse_offset(value.get("offset"))
    if "point" in value:
        target = PointRef(_text_value(value["point"], "click point"))
        return target if offset == Point(0, 0) else target.offset(x=offset.x, y=offset.y)
    if "search" in value:
        return ImageTarget(
            SearchRef(_text_value(value["search"], "click search")),
            min_confidence=_parse_optional_confidence(value.get("min_confidence")),
            offset=offset,
        )
    if "image" in value:
        return ImageTarget(
            ImageRef(_text_value(value["image"], "click image")),
            region=_parse_rect(value["region"], field="click image region") if "region" in value else None,
            min_confidence=_parse_optional_confidence(value.get("min_confidence")),
            offset=offset,
        )
    raise ValueError("click target must define one of point, search, or image")


def _parse_repeat(value: Any) -> Repeat:
    """解析 repeat 步骤。"""
    if not isinstance(value, dict):
        raise ValueError("repeat step must be an object")
    return Repeat(times=_int_value(value.get("times"), "repeat times"), steps=_parse_steps(value.get("steps")))


def _parse_if_state(value: Any) -> If:
    """解析状态条件分支步骤。"""
    if not isinstance(value, dict):
        raise ValueError("if_state step must be an object")
    return If(
        condition=_parse_screen_state_condition(value),
        then_steps=_parse_steps(value.get("then")),
        else_steps=() if "else" not in value else _parse_steps(value.get("else")),
    )


def _parse_wait_until_state(value: Any) -> WaitUntil:
    """解析等待状态步骤。"""
    if not isinstance(value, dict):
        raise ValueError("wait_until_state step must be an object")
    return WaitUntil(
        condition=_parse_screen_state_condition(value),
        timeout_seconds=_number_value(value.get("timeout"), "wait_until_state timeout"),
        interval_seconds=_number_value(value.get("interval"), "wait_until_state interval"),
    )


def _parse_screen_state_condition(value: dict[str, Any]) -> ScreenStateIs:
    """解析状态条件。"""
    return ScreenStateIs(
        _required_text(value, "state", "screen state"),
        min_confidence=_parse_optional_confidence(value.get("min_confidence")) or 0.8,
    )


def _parse_offset(value: Any) -> Point:
    """解析可选 offset。"""
    if value is None:
        return Point(0, 0)
    return _parse_point(value, field="offset")


def _parse_point(value: Any, *, field: str) -> Point:
    """解析 x/y 坐标对象。"""
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return Point(_int_value(value.get("x"), f"{field} x"), _int_value(value.get("y"), f"{field} y"))


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
