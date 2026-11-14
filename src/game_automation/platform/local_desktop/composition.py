"""本机桌面平台的 use case 装配。

本 module 负责把 portable application 用例接到原生窗口运行时；它是迁移
平台时优先替换的 composition 点，不解释任务步骤。真实运行不装配屏幕绝对坐标设备。
"""

from __future__ import annotations

from pathlib import Path

from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.application.project_assets import PROJECT_ROOT
from game_automation.portable.application.project_tasks import (
    load_project_task_catalog_result,
)
from game_automation.portable.application.task_run import TaskRunResult, run_task
from game_automation.portable.domain.task import FunctionTask


def run_task_on_local_desktop(
    task: FunctionTask,
    *,
    dry_run: bool,
    dry_run_color: str = "#000000",
    dry_run_images: tuple[str, ...] = (),
    dry_run_screen_state: str = "未知",
    project_root: Path = PROJECT_ROOT,
) -> TaskRunResult:
    """用原生窗口运行时或 dry-run 替身运行任务。"""
    return run_task(
        task,
        dry_run=dry_run,
        dry_run_color=dry_run_color,
        dry_run_images=dry_run_images,
        dry_run_screen_state=dry_run_screen_state,
        real_runtime_factory=None
        if dry_run
        else build_native_runtime_factory(project_root),
    )


def build_local_control_application(
    *,
    project_root: Path = PROJECT_ROOT,
) -> LocalControlApplication:
    """创建已接入原生窗口运行时的本地控制应用用例。"""
    catalog_result = load_project_task_catalog_result(project_root)
    return LocalControlApplication(
        project_root=project_root,
        catalog=catalog_result.catalog,
        task_config_errors=catalog_result.task_config_errors,
        real_runtime_factory=build_native_runtime_factory(project_root),
    )


def build_native_runtime_factory(project_root: Path):
    """延迟导入原生工厂；每个控制应用保留独立租约，不共享采集源。"""
    from game_automation.platform.macos.adapters.window_runtime import (
        MacOSRuntimeFactory,
    )

    return MacOSRuntimeFactory(project_root)
