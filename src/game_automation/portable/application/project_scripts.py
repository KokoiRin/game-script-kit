"""组装项目可用脚本 catalog。

本 module 负责把内置脚本和项目 `scripts/*.json` 文件脚本合并为一个
ScriptCatalog；它不执行脚本、不解析 CLI/UI 参数，也不创建平台 adapter。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.config_script_loader import (
    ScriptConfigError,
    load_config_scripts_with_errors,
)
from game_automation.portable.application.project_assets import image_asset_root, script_root
from game_automation.portable.domain import Script
from game_automation.portable.scripts_manager.catalog import DEFAULT_SCRIPT_CATALOG, ScriptCatalog


@dataclass(frozen=True, slots=True)
class ProjectScriptCatalogResult:
    catalog: ScriptCatalog
    script_config_errors: tuple[ScriptConfigError, ...] = ()


def load_project_script_catalog(
    project_root: Path,
    *,
    base_catalog: ScriptCatalog = DEFAULT_SCRIPT_CATALOG,
) -> ScriptCatalog:
    """加载项目脚本目录并合并到给定基础 catalog。"""
    return load_project_script_catalog_result(project_root, base_catalog=base_catalog).catalog


def load_project_script_catalog_result(
    project_root: Path,
    *,
    base_catalog: ScriptCatalog = DEFAULT_SCRIPT_CATALOG,
) -> ProjectScriptCatalogResult:
    """加载项目脚本目录，返回可用 catalog 和被隔离的配置错误。"""
    base_scripts = tuple(base_catalog.get(name) for name in base_catalog.list_names())
    config_result = load_config_scripts_with_errors(
        script_root(project_root),
        asset_root=image_asset_root(project_root),
    )
    scripts: list[Script] = list(base_scripts)
    errors: list[ScriptConfigError] = list(config_result.errors)
    seen_names = {script.name for script in scripts}
    for entry in config_result.entries:
        if entry.script.name in seen_names:
            errors.append(
                ScriptConfigError(
                    entry.file,
                    f"{entry.file}: duplicate script name: {entry.script.name}",
                )
            )
            continue
        scripts.append(entry.script)
        seen_names.add(entry.script.name)
    return ProjectScriptCatalogResult(
        catalog=ScriptCatalog(tuple(scripts)),
        script_config_errors=tuple(errors),
    )
