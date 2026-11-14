"""表达任务运行过程中的结构化事件。

本 module 只定义 engine/application 之间共享的运行事件和值到文本的转换；
它不执行任务、不访问平台 adapter，也不处理 UI 渲染。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TaskRunEvent:
    """记录任务运行中的一个可观察事件。"""

    event_type: str
    step_path: str = ""
    step_type: str = ""
    status: str = ""
    details: dict[str, str] = field(default_factory=dict)


def emit_task_run_event(logger, event: TaskRunEvent) -> None:
    """把结构化事件交给 logger，没有结构化接口时退化为文本日志。"""
    if logger is None:
        return
    log_event = getattr(logger, "log_event", None)
    if log_event is not None:
        log_event(event)
        return
    logger.log(format_task_run_event(event))


def format_task_run_event(event: TaskRunEvent) -> str:
    """把运行事件格式化为当前 UI 日志区可直接展示的一行文本。"""
    parts = [f"task event type={event.event_type}"]
    if event.step_path:
        parts.append(f"path={event.step_path}")
    if event.step_type:
        parts.append(f"step={event.step_type}")
    if event.status:
        parts.append(f"status={event.status}")
    parts.extend(f"{key}={value}" for key, value in event.details.items())
    return " ".join(parts)


def task_run_event_to_payload(event: TaskRunEvent) -> dict[str, object]:
    """把运行事件转换成入口可序列化的 payload。"""
    return {
        "type": event.event_type,
        "path": event.step_path,
        "step": event.step_type,
        "status": event.status,
        "details": dict(event.details),
    }
