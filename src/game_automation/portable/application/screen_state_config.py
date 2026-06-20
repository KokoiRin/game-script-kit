"""读取本地界面状态识别配置。

本 module 负责把 assets/screen-states.json 转换成状态探测候选；它不执行图片
匹配、不截图，也不创建平台 adapter。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from game_automation.portable.domain import (
    ImageSearchSpec,
    ImageTemplate,
    NamedImageSearch,
    NamedRegion,
    Rect,
    RegionRef,
    ScreenStateCandidate,
    SearchRef,
    TargetCatalog,
)


@dataclass(frozen=True, slots=True)
class ScreenStateConfigSearchSummary:
    name: str
    image: str
    region: str
    min_confidence: float | None = None


@dataclass(frozen=True, slots=True)
class ScreenStateConfigGroupSummary:
    state: str
    searches: tuple[ScreenStateConfigSearchSummary, ...]


@dataclass(frozen=True, slots=True)
class _ParsedScreenStateConfig:
    catalog: TargetCatalog
    candidate_refs: tuple[tuple[str, str], ...]


def load_screen_state_candidates(
    config_path: Path,
    *,
    asset_root: Path,
    supported_suffixes: frozenset[str],
) -> tuple[ScreenStateCandidate, ...] | None:
    """读取状态组配置文件，不存在时返回 None。"""
    data = _load_screen_state_config(config_path)
    if data is None:
        return None

    parsed = _parse_screen_state_config(
        data,
        asset_root=asset_root,
        supported_suffixes=supported_suffixes,
    )
    return tuple(
        ScreenStateCandidate(
            state,
            parsed.catalog.resolve_search(SearchRef(search_name)),
            search_name=search_name,
        )
        for state, search_name in parsed.candidate_refs
    )


def load_screen_state_target_catalog(
    config_path: Path,
    *,
    asset_root: Path,
    supported_suffixes: frozenset[str],
) -> TargetCatalog | None:
    """读取状态配置并转换成脚本可复用的共享资源目录。"""
    data = _load_screen_state_config(config_path)
    if data is None:
        return None
    return _parse_screen_state_config(
        data,
        asset_root=asset_root,
        supported_suffixes=supported_suffixes,
    ).catalog


def load_screen_state_regions(config_path: Path) -> tuple[NamedRegion, ...] | None:
    """读取状态配置中的命名区域，不存在时返回 None。"""
    data = _load_screen_state_config(config_path)
    if data is None:
        return None
    return _parse_regions(data.get("regions", {}))


def load_screen_state_names(config_path: Path) -> tuple[str, ...] | None:
    """读取状态配置中的状态名称并按首次出现顺序去重。"""
    data = _load_screen_state_config(config_path)
    if data is None:
        return None

    groups = data.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("screen state config groups must be a non-empty list")

    names = []
    seen = set()
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("screen state group must be an object")
        state = _required_text(group, "state", "screen state group state")
        if state not in seen:
            seen.add(state)
            names.append(state)
    return tuple(names)


def load_screen_state_config_summary(
    config_path: Path,
    *,
    asset_root: Path,
    supported_suffixes: frozenset[str],
) -> tuple[ScreenStateConfigGroupSummary, ...] | None:
    """读取状态配置并转换成用户可读摘要，不存在时返回 None。"""
    data = _load_screen_state_config(config_path)
    if data is None:
        return None

    regions = _parse_regions(data.get("regions", {}))
    region_names = {region.name for region in regions}
    groups = data.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("screen state config groups must be a non-empty list")

    summaries = []
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("screen state group must be an object")
        state = _required_text(group, "state", "screen state group state")
        search_items = group.get("searches")
        if not isinstance(search_items, list) or not search_items:
            raise ValueError(f"screen state group searches must be non-empty: {state}")
        summaries.append(
            ScreenStateConfigGroupSummary(
                state,
                tuple(
                    _screen_state_search_summary(
                        state,
                        search_item,
                        search_index=search_index,
                        asset_root=asset_root,
                        supported_suffixes=supported_suffixes,
                        region_names=region_names,
                    )
                    for search_index, search_item in enumerate(search_items)
                ),
            )
        )
    return tuple(summaries)


def _parse_screen_state_config(
    data: dict[str, Any],
    *,
    asset_root: Path,
    supported_suffixes: frozenset[str],
) -> _ParsedScreenStateConfig:
    """解析状态配置中可执行搜索所需的资源目录和候选引用。"""
    regions = _parse_regions(data.get("regions", {}))
    searches: list[NamedImageSearch] = []
    candidate_refs: list[tuple[str, str]] = []
    groups = data.get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("screen state config groups must be a non-empty list")

    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("screen state group must be an object")
        state = _required_text(group, "state", "screen state group state")
        search_items = group.get("searches")
        if not isinstance(search_items, list) or not search_items:
            raise ValueError(f"screen state group searches must be non-empty: {state}")
        for search_index, search_item in enumerate(search_items):
            if not isinstance(search_item, dict):
                raise ValueError("screen state search must be an object")
            search_name = _screen_state_search_name(state, search_item, search_index=search_index)
            searches.append(
                NamedImageSearch(
                    search_name,
                    ImageSearchSpec(
                        ImageTemplate(
                            str(
                                _resolve_asset_image(
                                    _required_text(
                                        search_item,
                                        "image",
                                        "screen state search image",
                                    ),
                                    asset_root=asset_root,
                                    supported_suffixes=supported_suffixes,
                                )
                            )
                        ),
                        region=_parse_region_ref(search_item.get("region")),
                        min_confidence=_parse_optional_confidence(search_item.get("min_confidence")),
                    ),
                )
            )
            candidate_refs.append((state, search_name))

    return _ParsedScreenStateConfig(
        catalog=TargetCatalog(regions=tuple(regions), searches=tuple(searches)),
        candidate_refs=tuple(candidate_refs),
    )


def _load_screen_state_config(config_path: Path) -> dict[str, Any] | None:
    """读取状态配置 JSON object，不存在时返回 None。"""
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid screen state config json: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("screen state config must be an object")
    return data


def _screen_state_search_summary(
    state: str,
    search_item: Any,
    *,
    search_index: int,
    asset_root: Path,
    supported_suffixes: frozenset[str],
    region_names: set[str],
) -> ScreenStateConfigSearchSummary:
    """把单个搜索项转换成用户可读摘要并复用配置校验规则。"""
    if not isinstance(search_item, dict):
        raise ValueError("screen state search must be an object")
    search_name = _screen_state_search_name(state, search_item, search_index=search_index)
    image = _required_text(search_item, "image", "screen state search image")
    _resolve_asset_image(image, asset_root=asset_root, supported_suffixes=supported_suffixes)
    region_ref = _parse_region_ref(search_item.get("region"))
    return ScreenStateConfigSearchSummary(
        name=search_name,
        image=image,
        region=_summarize_region(region_ref, region_names=region_names),
        min_confidence=_parse_optional_confidence(search_item.get("min_confidence")),
    )


def _screen_state_search_name(
    state: str,
    search_item: dict[str, Any],
    *,
    search_index: int,
) -> str:
    """解析搜索项名称，缺省时使用状态名和序号生成稳定名称。"""
    search_name = search_item.get("name")
    if search_name is None:
        search_name = f"{state}:{search_index + 1}"
    if not isinstance(search_name, str) or not search_name.strip():
        raise ValueError("screen state search name cannot be empty")
    return search_name


def _summarize_region(region: Rect | RegionRef | None, *, region_names: set[str]) -> str:
    """把搜索区域转换成 UI 可展示文本，并校验命名区域存在。"""
    if region is None:
        return "全屏"
    if isinstance(region, RegionRef):
        if region.name not in region_names:
            raise LookupError(f"unknown region target: {region.name}")
        return region.name
    return (
        f"left={region.left}, top={region.top}, "
        f"width={region.width}, height={region.height}"
    )


def _parse_regions(value: Any) -> tuple[NamedRegion, ...]:
    """解析配置中的命名区域表。"""
    if not isinstance(value, dict):
        raise ValueError("screen state config regions must be an object")
    regions = []
    for name, region_value in value.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("screen state region name cannot be empty")
        regions.append(NamedRegion(name, _parse_rect(region_value, f"screen state region: {name}")))
    return tuple(regions)


def _parse_region_ref(value: Any) -> Rect | RegionRef | None:
    """解析搜索项上的区域引用或内联区域。"""
    if value is None:
        return None
    if isinstance(value, str):
        return RegionRef(value)
    return _parse_rect(value, "screen state search region")


def _parse_rect(value: Any, label: str) -> Rect:
    """解析 JSON object 形式的矩形区域。"""
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    try:
        return Rect(
            left=int(value["left"]),
            top=int(value["top"]),
            width=int(value["width"]),
            height=int(value["height"]),
        )
    except KeyError as exc:
        raise ValueError(f"{label} missing field: {exc.args[0]}") from exc


def _parse_optional_confidence(value: Any) -> float | None:
    """解析可选最低置信度。"""
    if value is None:
        return None
    confidence = float(value)
    if not 0 < confidence <= 1:
        raise ValueError("screen state search min_confidence must be greater than 0 and at most 1")
    return confidence


def _required_text(item: dict[str, Any], key: str, label: str) -> str:
    """读取必填文本字段并拒绝空白值。"""
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} cannot be empty")
    return value


def _resolve_asset_image(
    image: str,
    *,
    asset_root: Path,
    supported_suffixes: frozenset[str],
) -> Path:
    """解析状态配置中的图片路径并限制在 assets 目录内。"""
    candidate = (asset_root / image).resolve()
    resolved_asset_root = asset_root.resolve()
    try:
        candidate.relative_to(resolved_asset_root)
    except ValueError as exc:
        raise ValueError("screen state search image must stay inside assets folder") from exc
    if not candidate.is_file() or candidate.suffix.lower() not in supported_suffixes:
        raise ValueError("screen state search image does not exist or has unsupported suffix")
    return candidate
