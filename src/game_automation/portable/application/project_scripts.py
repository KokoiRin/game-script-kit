"""组装项目可用脚本 catalog。

本 module 负责把基础 catalog 的图片资源绑定到数据根，再合并工作区 Python
任务。它不执行脚本、不解析 CLI/UI 参数，也不创建平台 adapter。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from game_automation.portable.application.project_assets import (
    image_asset_root,
    script_root,
)
from game_automation.portable.application.task_discovery import (
    TaskLoadError,
    discover_task_files,
)
from game_automation.portable.domain import ImageTemplate
from game_automation.portable.domain.task import FunctionTask
from game_automation.portable.scripts_manager.catalog import ScriptCatalog


@dataclass(frozen=True, slots=True)
class ProjectScriptCatalogResult:
    catalog: ScriptCatalog
    script_config_errors: tuple[TaskLoadError, ...] = ()


def load_project_script_catalog(
    project_root: Path,
    *,
    base_catalog: ScriptCatalog | None = None,
) -> ScriptCatalog:
    """加载项目脚本目录并合并到给定基础 catalog。"""
    return load_project_script_catalog_result(
        project_root, base_catalog=base_catalog
    ).catalog


def load_project_script_catalog_result(
    project_root: Path,
    *,
    base_catalog: ScriptCatalog | None = None,
) -> ProjectScriptCatalogResult:
    """加载项目脚本目录，返回可用 catalog 和被隔离的配置错误。"""
    base_catalog = base_catalog if base_catalog is not None else ScriptCatalog()
    base_scripts = tuple(
        _bind_base_script_resources(base_catalog.get(name), project_root)
        for name in base_catalog.list_names()
    )
    discovered = discover_task_files(
        script_root(project_root), asset_root=image_asset_root(project_root)
    )
    scripts: list[FunctionTask] = list(base_scripts)
    errors = list(discovered.errors)
    seen_names = {script.name for script in scripts}
    for entry in discovered.entries:
        if entry.script.name in seen_names:
            errors.append(
                TaskLoadError(
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


def _bind_base_script_resources(
    script: FunctionTask, project_root: Path
) -> FunctionTask:
    """把基础脚本图片资源的相对路径绑定到数据根，保留原始脚本定义。"""
    images = tuple(
        replace(image, template=_bind_template_path(image.template, project_root))
        for image in script.resources.images
    )
    searches = tuple(
        replace(
            named,
            search=replace(
                named.search,
                image=_bind_template_path(named.search.image, project_root),
            ),
        )
        if isinstance(named.search.image, ImageTemplate)
        else named
        for named in script.resources.searches
    )
    if images == script.resources.images and searches == script.resources.searches:
        return script
    return replace(
        script, resources=replace(script.resources, images=images, searches=searches)
    )


def _bind_template_path(template: ImageTemplate, project_root: Path) -> ImageTemplate:
    """只绑定资源表中的相对图片路径，绝对路径保持原有含义。"""
    if Path(template.path).is_absolute():
        return template
    return ImageTemplate(str((project_root / template.path).resolve()))
