"""组装脚本运行前可复用的资源目录。

本 module 负责把项目配置中的共享资源合并到 Script 上；它不解释脚本步骤、
不执行脚本，也不创建平台 adapter。
"""

from __future__ import annotations

from pathlib import Path

from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_SUFFIXES,
    image_asset_root,
    screen_state_config_path,
)
from game_automation.portable.application.screen_state_config import load_screen_state_target_catalog
from game_automation.portable.domain import Script, TargetCatalog


def load_shared_script_resources(project_root: Path) -> TargetCatalog | None:
    """读取项目配置中可供脚本复用的共享资源目录。"""
    return load_screen_state_target_catalog(
        screen_state_config_path(project_root),
        asset_root=image_asset_root(project_root),
        supported_suffixes=IMAGE_ASSET_SUFFIXES,
    )


def script_with_shared_resources(script: Script, shared: TargetCatalog | None) -> Script:
    """把共享资源合并进脚本，脚本局部资源保留覆盖权。"""
    if shared is None:
        return script
    resources = merge_target_catalogs(shared, script.resources)
    if resources == script.resources:
        return script
    return Script(
        name=script.name,
        window=script.window,
        steps=script.steps,
        resources=resources,
    )


def merge_target_catalogs(shared: TargetCatalog, local: TargetCatalog) -> TargetCatalog:
    """合并共享和脚本局部资源，局部资源覆盖同名共享资源。"""
    return TargetCatalog(
        points=_merge_named_resources(shared.points, local.points),
        images=_merge_named_resources(shared.images, local.images),
        regions=_merge_named_resources(shared.regions, local.regions),
        searches=_merge_named_resources(shared.searches, local.searches),
    )


def _merge_named_resources(shared, local):
    """按名称合并资源元组。"""
    local_names = {item.name for item in local}
    return (*tuple(item for item in shared if item.name not in local_names), *local)
