"""组装项目可用脚本 catalog。

本 module 负责把内置脚本和项目 `scripts/*.json` 文件脚本合并为一个
ScriptCatalog；它不执行脚本、不解析 CLI/UI 参数，也不创建平台 adapter。
"""

from __future__ import annotations

from pathlib import Path

from game_automation.portable.application.config_script_loader import load_config_scripts
from game_automation.portable.application.project_assets import image_asset_root, script_root
from game_automation.portable.scripts_manager.catalog import DEFAULT_SCRIPT_CATALOG, ScriptCatalog


def load_project_script_catalog(
    project_root: Path,
    *,
    base_catalog: ScriptCatalog = DEFAULT_SCRIPT_CATALOG,
) -> ScriptCatalog:
    """加载项目脚本目录并合并到给定基础 catalog。"""
    base_scripts = tuple(base_catalog.get(name) for name in base_catalog.list_names())
    file_scripts = load_config_scripts(script_root(project_root), asset_root=image_asset_root(project_root))
    return ScriptCatalog((*base_scripts, *file_scripts))
