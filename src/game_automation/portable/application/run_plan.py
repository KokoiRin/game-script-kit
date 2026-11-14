"""编排一轮多个任务运行的 application module。

本 module 负责按用户给定顺序运行已有任务、应用停止策略并聚合结果；它不解析
CLI 参数、不读取项目任务目录，也不解释单个任务步骤语义。
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from game_automation.portable.domain.task import FunctionTask


@dataclass(frozen=True, slots=True)
class TaskPlanItem:
    """描述一轮计划里的单个任务项。"""

    name: str
    task: FunctionTask
    dry_run_images: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TaskPlanRunResult:
    """表达单个任务运行后可被计划聚合的结果。"""

    exit_code: int
    finish_reason: str = "completed"
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True, slots=True)
class TaskPlanItemResult:
    """记录计划中某个任务项的执行结果。"""

    index: int
    task_name: str
    exit_code: int
    finish_reason: str
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True, slots=True)
class TaskPlanResult:
    """记录一轮计划的整体结果。"""

    exit_code: int
    finish_reason: str
    items: tuple[TaskPlanItemResult, ...]


RunPlanItemRunner = Callable[[TaskPlanItem], TaskPlanRunResult]


def run_task_plan(
    items: Sequence[TaskPlanItem],
    *,
    run_item: RunPlanItemRunner,
    continue_on_error: bool = False,
) -> TaskPlanResult:
    """按顺序运行一轮任务计划，并根据失败策略决定是否继续。"""
    item_results: list[TaskPlanItemResult] = []
    first_error_code = 0
    first_incomplete_reason = "completed"
    for index, item in enumerate(items, start=1):
        result = run_item(item)
        item_result = TaskPlanItemResult(
            index=index,
            task_name=item.name,
            exit_code=result.exit_code,
            finish_reason=result.finish_reason,
            stdout=result.stdout,
            stderr=result.stderr,
        )
        item_results.append(item_result)
        # 取消是整轮停止请求，优先于普通失败后的继续与聚合策略。
        if result.finish_reason == "cancelled":
            return TaskPlanResult(
                exit_code=130,
                finish_reason="cancelled",
                items=tuple(item_results),
            )
        # 资源尚未停止时不能继续建立新的运行环境，即使允许普通失败后继续。
        if result.finish_reason == "cleanup_failed":
            return TaskPlanResult(
                exit_code=result.exit_code or 1,
                finish_reason="cleanup_failed",
                items=tuple(item_results),
            )
        incomplete = result.exit_code != 0 or result.finish_reason != "completed"
        if incomplete and first_incomplete_reason == "completed":
            first_incomplete_reason = (
                result.finish_reason
                if result.finish_reason != "completed"
                else "failed"
            )
        if result.exit_code != 0:
            if first_error_code == 0:
                first_error_code = result.exit_code
        if incomplete and not continue_on_error:
            break
    exit_code = first_error_code
    return TaskPlanResult(
        exit_code=exit_code,
        finish_reason=first_incomplete_reason,
        items=tuple(item_results),
    )
