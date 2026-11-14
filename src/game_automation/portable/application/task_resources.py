"""组装任务运行前可复用的资源目录。

本 module 负责把窗口规则中的共享资源合并到函数任务上；它不解释任务步骤、
不执行任务，也不创建平台 adapter。状态与共享搜索只读取 window-states.json。
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_SUFFIXES,
    image_asset_root,
)
from game_automation.portable.application.screen_state_config import (
    load_screen_state_target_catalog,
)
from game_automation.portable.application.task_dependencies import (
    task_needs_shared_resources,
)
from game_automation.portable.application.window_state_rules import rules_path
from game_automation.portable.domain import TargetCatalog
from game_automation.portable.domain.task import FunctionTask


def prepare_task_resources(task: FunctionTask, project_root: Path) -> FunctionTask:
    """仅在局部资源不足时加载共享搜索，隔离无关状态配置错误。"""
    if not task_needs_shared_resources(task):
        return task
    return task_with_shared_resources(task, load_shared_task_resources(project_root))


def load_shared_task_resources(project_root: Path) -> TargetCatalog | None:
    """读取窗口规则中可供任务复用的共享资源目录。"""
    return load_screen_state_target_catalog(
        rules_path(project_root),
        asset_root=image_asset_root(project_root),
        supported_suffixes=IMAGE_ASSET_SUFFIXES,
    )


def task_with_shared_resources(
    task: FunctionTask, shared: TargetCatalog | None
) -> FunctionTask:
    """把共享资源合并进任务，任务局部资源保留覆盖权。"""
    if shared is None:
        return task
    resources = merge_target_catalogs(shared, task.resources)
    if resources == task.resources:
        return task
    return replace(task, resources=resources)


def merge_target_catalogs(shared: TargetCatalog, local: TargetCatalog) -> TargetCatalog:
    """合并共享和任务局部资源，局部资源覆盖同名共享资源。"""
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


def task_state_config_path(task: FunctionTask | None, project_root: Path) -> Path:
    """返回窗口规则路径，供 CLI 和控制台的依赖检查使用。"""
    del task
    return rules_path(project_root)
