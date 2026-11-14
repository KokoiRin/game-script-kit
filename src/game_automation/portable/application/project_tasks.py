"""组装项目可用任务 catalog。

本 module 负责把基础 catalog 的图片资源绑定到数据根，再合并工作区 Python
任务。它不执行任务、不解析 CLI/UI 参数，也不创建平台 adapter。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from game_automation.portable.application.project_assets import (
    image_asset_root,
    task_root,
)
from game_automation.portable.application.task_catalog import TaskCatalog
from game_automation.portable.application.task_discovery import (
    TaskLoadError,
    discover_task_files,
)
from game_automation.portable.domain import ImageTemplate
from game_automation.portable.domain.task import FunctionTask


@dataclass(frozen=True, slots=True)
class ProjectTaskCatalogResult:
    catalog: TaskCatalog
    task_config_errors: tuple[TaskLoadError, ...] = ()


def load_project_task_catalog(
    project_root: Path,
    *,
    base_catalog: TaskCatalog | None = None,
) -> TaskCatalog:
    """加载项目任务目录并合并到给定基础 catalog。"""
    return load_project_task_catalog_result(
        project_root, base_catalog=base_catalog
    ).catalog


def load_project_task_catalog_result(
    project_root: Path,
    *,
    base_catalog: TaskCatalog | None = None,
) -> ProjectTaskCatalogResult:
    """加载项目任务目录，返回可用 catalog 和被隔离的配置错误。"""
    base_catalog = base_catalog if base_catalog is not None else TaskCatalog()
    base_tasks = tuple(
        _bind_base_task_resources(base_catalog.get(name), project_root)
        for name in base_catalog.list_names()
    )
    discovered = discover_task_files(
        task_root(project_root), asset_root=image_asset_root(project_root)
    )
    tasks: list[FunctionTask] = list(base_tasks)
    errors = list(discovered.errors)
    seen_names = {task.name for task in tasks}
    for entry in discovered.entries:
        if entry.task.name in seen_names:
            errors.append(
                TaskLoadError(
                    entry.file,
                    f"{entry.file}: duplicate task name: {entry.task.name}",
                )
            )
            continue
        tasks.append(entry.task)
        seen_names.add(entry.task.name)
    return ProjectTaskCatalogResult(
        catalog=TaskCatalog(tuple(tasks)),
        task_config_errors=tuple(errors),
    )


def _bind_base_task_resources(task: FunctionTask, project_root: Path) -> FunctionTask:
    """把基础任务图片资源的相对路径绑定到数据根，保留原始任务定义。"""
    images = tuple(
        replace(image, template=_bind_template_path(image.template, project_root))
        for image in task.resources.images
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
        for named in task.resources.searches
    )
    if images == task.resources.images and searches == task.resources.searches:
        return task
    return replace(
        task, resources=replace(task.resources, images=images, searches=searches)
    )


def _bind_template_path(template: ImageTemplate, project_root: Path) -> ImageTemplate:
    """只绑定资源表中的相对图片路径，绝对路径保持原有含义。"""
    if Path(template.path).is_absolute():
        return template
    return ImageTemplate(str((project_root / template.path).resolve()))
