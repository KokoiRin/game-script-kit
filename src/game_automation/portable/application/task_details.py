"""生成本地 UI 可展示的任务详情。

本 module 负责把函数任务声明转换成只读摘要和运行前依赖检查；它不运行任务、
不读取屏幕，也不处理 UI 展示细节。LocalControlApplication 调用这里作为
任务 catalog 到 UI adapter 之间的 presenter seam。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.task_dependencies import (
    describe_task_dependencies,
)
from game_automation.portable.domain.task import FunctionTask
from game_automation.portable.domain.task_analysis import analyze_task


@dataclass(frozen=True, slots=True)
class TaskDetailsResult:
    exit_code: int
    name: str
    steps: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    state_dependencies: tuple[str, ...] = ()
    point_dependencies: tuple[str, ...] = ()
    image_dependencies: tuple[str, ...] = ()
    readiness: tuple[tuple[str, str, str], ...] = ()
    stderr: str = ""


def describe_task_details(
    task: FunctionTask,
    *,
    asset_root: Path,
    supported_image_suffixes: frozenset[str],
    state_names: tuple[str, ...] | None,
) -> TaskDetailsResult:
    """生成任务详情结果。"""
    analysis = analyze_task(task)
    dependency_details = describe_task_dependencies(
        task,
        asset_root=asset_root,
        supported_image_suffixes=supported_image_suffixes,
        state_names=state_names,
        analysis=analysis,
    )
    missing = tuple(
        label
        for label, status, _ in dependency_details.readiness
        if status == "missing"
    )
    return TaskDetailsResult(
        exit_code=2 if missing else 0,
        name=task.name,
        steps=(f"Python run(ctx) · {task.source_path}", "实际执行路径见运行日志"),
        dependencies=dependency_details.dependencies,
        state_dependencies=dependency_details.state_dependencies,
        point_dependencies=dependency_details.point_dependencies,
        image_dependencies=dependency_details.image_dependencies,
        readiness=dependency_details.readiness,
        stderr=f"任务依赖缺失：{'、'.join(missing)}\n" if missing else "",
    )
