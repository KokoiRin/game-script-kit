"""编排单次任务运行的应用 module。

本 module 负责选择 dry-run 或原生窗口会话、补齐运行端口、调用任务，
并把运行配置、setup 和超时错误归一化；它不做任务注册表查找，也不打印 CLI 输出。
真实运行只接受显式原生窗口目标，不回退到屏幕绝对坐标。
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, replace
from time import monotonic

from game_automation.portable.adapters.dry_run import (
    DryRunInputDevice,
    DryRunPixelColorReader,
    DryRunScreenImageLocator,
    DryRunScreenStateReader,
)
from game_automation.portable.application.function_task_run import run_function_task
from game_automation.portable.application.runtime_ports import (
    RuntimeFactory,
    RuntimePorts,
)
from game_automation.portable.application.task_dependencies import (
    validate_task_resource_references,
)
from game_automation.portable.domain import (
    Color,
    ImageMatch,
    ImageTemplate,
    Rect,
)
from game_automation.portable.domain.task import FunctionTask
from game_automation.portable.engine.cancellation import (
    RunCancelled,
    TaskCancelledError,
)
from game_automation.portable.engine.ports import (
    CancellationToken,
    InputDevice,
    PixelColorReader,
    RunLogger,
    ScreenImageLocator,
    ScreenStateReader,
)
from game_automation.portable.engine.run_events import (
    TaskRunEvent,
    emit_task_run_event,
)
from game_automation.portable.engine.runtime_requirements import (
    inspect_runtime_requirements,
)
from game_automation.portable.engine.task_context import TargetNotFound, TaskContext

_REAL_TARGET_REQUIRED = (
    "real run requires target.backend macos-window or macos-window-background"
)


@dataclass(frozen=True, slots=True)
class TaskRunResult:
    exit_code: int
    error_message: str | None = None
    finish_reason: str = "completed"


def run_task(
    task: FunctionTask,
    *,
    dry_run: bool,
    dry_run_color: str = "#000000",
    dry_run_images: tuple[str, ...] = (),
    dry_run_screen_state: str = "未知",
    real_runtime_factory: RuntimeFactory | None = None,
    cancellation_token: CancellationToken | None = None,
    logger: RunLogger | None = None,
    emit_step_events: bool = False,
) -> TaskRunResult:
    """运行一份已解析任务，并返回入口层可直接映射的结果。"""
    if emit_step_events:
        _emit_run_lifecycle_event(
            logger,
            "run_started",
            details={"task": task.name, "dry_run": str(dry_run)},
        )
    stack = ExitStack()
    stage = "setup"
    execution_message = None
    result = TaskRunResult(1, "task run did not finish", "failed")
    try:
        validate_task_resource_references(task)
        if dry_run:
            prepared_task = task
            ports = _build_dry_run_ports(
                task,
                dry_run_color=dry_run_color,
                dry_run_images=dry_run_images,
                dry_run_screen_state=dry_run_screen_state,
            )
        else:
            prepared_task, ports = _open_native_ports(
                task,
                real_runtime_factory=real_runtime_factory,
                cancellation_token=cancellation_token,
                logger=logger,
                stack=stack,
            )
        if not dry_run and cancellation_token is not None:
            ports = replace(
                ports, device=_CancellableInputDevice(ports.device, cancellation_token)
            )
        clock = ports.device.clock if dry_run else monotonic
        if ports.control is not None:
            clock = ports.control.task_time
        context = TaskContext(
            ports.window,
            prepared_task.resources,
            device=ports.device,
            clock=clock,
            color_reader=ports.color_reader,
            image_locator=ports.image_locator,
            screen_state_reader=ports.screen_state_reader,
            runtime_control=ports.control,
            cancellation_token=cancellation_token,
            logger=logger,
            emit_step_events=emit_step_events,
        )
        stage = "run"
        run_function_task(prepared_task, context, cancellation_token=cancellation_token)
        result = TaskRunResult(0)
    except (TaskCancelledError, RunCancelled) as exc:
        result = TaskRunResult(130, str(exc), "cancelled")
    except Exception as exc:
        if stage == "setup":
            reason = (
                "configuration_failed"
                if isinstance(exc, (LookupError, ValueError))
                else "setup_failed"
            )
            result = TaskRunResult(
                2 if reason == "configuration_failed" else 1,
                f"task run {'configuration' if reason == 'configuration_failed' else 'setup'} failed: {exc}",
                reason,
            )
        elif isinstance(exc, TargetNotFound):
            result = TaskRunResult(0, finish_reason="stopped_unmet_condition")
            execution_message = str(exc)
        elif isinstance(exc, TimeoutError):
            result = TaskRunResult(1, f"task run timed out: {exc}", "timed_out")
        else:
            result = TaskRunResult(1, f"task run failed: {exc}", "failed")
    finally:
        try:
            stack.close()
        except Exception as exc:
            message = f"runtime cleanup failed: {exc}"
            if logger is not None:
                logger.log(message)
            execution_error = result.error_message or execution_message
            if execution_error:
                message = f"{execution_error}\n{message}"
            if result.finish_reason == "cancelled":
                result = replace(result, error_message=message)
            else:
                result = TaskRunResult(1, message, "cleanup_failed")
    # 停流可能等待回调屏障；此期间到达的取消仍高于完成和清理失败。
    if cancellation_token is not None and cancellation_token.is_cancelled():
        result = TaskRunResult(
            130, result.error_message or "task run cancelled", "cancelled"
        )
    details = {"exit_code": str(result.exit_code)}
    if result.exit_code == 0 and result.finish_reason != "completed":
        details["reason"] = execution_message or ""
    if result.error_message is not None:
        details["error"] = result.error_message
    _emit_run_lifecycle_event(
        logger,
        "run_finished",
        status=result.finish_reason,
        details=details,
        enabled=emit_step_events,
    )
    return result


def _open_native_ports(
    task: FunctionTask,
    *,
    real_runtime_factory: RuntimeFactory | None,
    cancellation_token: CancellationToken | None,
    logger: RunLogger | None,
    stack: ExitStack,
) -> tuple[FunctionTask, RuntimePorts]:
    """打开唯一的原生窗口会话，并拒绝任何屏幕绝对坐标回退。"""
    if task.target is None or not task.target.uses_native_window:
        raise ValueError(_REAL_TARGET_REQUIRED)
    if real_runtime_factory is None:
        raise RuntimeError(
            f"{task.target.backend} runtime factory is required; desktop fallback is disabled"
        )
    if logger is not None:
        logger.log(
            f"runtime selected backend={task.target.backend} target={task.target.application!r} title={task.target.window_title!r}"
        )
    requirements = inspect_runtime_requirements(task)
    ports = stack.enter_context(
        real_runtime_factory.open(task.target, requirements, cancellation_token, logger)
    )
    for needed, port, name in (
        (True, ports.device, "device"),
        (requirements.needs_color_reader, ports.color_reader, "color reader"),
        (
            requirements.needs_image_locator,
            ports.image_locator,
            "image locator",
        ),
        (
            requirements.needs_screen_state_reader,
            ports.screen_state_reader,
            "screen state reader",
        ),
    ):
        if needed and port is None:
            raise RuntimeError(
                f"{task.target.backend} runtime did not supply required {name}"
            )
    return replace(task, window=ports.window), ports


def _build_dry_run_ports(
    task: FunctionTask,
    *,
    dry_run_color: str,
    dry_run_images: tuple[str, ...],
    dry_run_screen_state: str,
) -> RuntimePorts:
    """用固定替身运行，不打开窗口、不读取状态文件、不接触桌面。"""
    requirements = inspect_runtime_requirements(task)
    return RuntimePorts(
        task.window,
        DryRunInputDevice(),
        color_reader=_build_dry_run_color_reader(
            dry_run_color, needs_color_reader=requirements.needs_color_reader
        ),
        image_locator=_build_dry_run_image_locator(
            dry_run_images, needs_image_locator=requirements.needs_image_locator
        ),
        screen_state_reader=_build_dry_run_screen_state_reader(
            dry_run_screen_state,
            needs_screen_state_reader=requirements.needs_screen_state_reader,
        ),
    )


@dataclass(frozen=True, slots=True)
class _CancellableInputDevice:
    """维持设备原子输入契约，并将真实等待拆成可取消的短片段。"""

    device: InputDevice
    cancellation: CancellationToken

    def click(self, target) -> None:
        """保持点击操作由真实设备一次完成。"""
        self.device.click(target)

    def hotkey(self, keys) -> None:
        """保持组合键及失败释放逻辑在真实设备内完成。"""
        self.device.hotkey(keys)

    def drag_to(self, start, end, duration_seconds=0.0) -> None:
        """保持拖拽操作由真实设备一次完成。"""
        self.device.drag_to(start, end, duration_seconds)

    def wait(self, duration_seconds: float) -> None:
        """每至多 50 毫秒检查取消，避免退出被固定长等待阻塞。"""
        if duration_seconds == 0:
            self.device.wait(0)
            return
        remaining = duration_seconds
        while remaining > 1e-9:
            if self.cancellation.is_cancelled():
                raise TaskCancelledError("task run cancelled")
            interval = min(remaining, 0.05)
            self.device.wait(interval)
            remaining -= interval


def _emit_run_lifecycle_event(
    logger: RunLogger | None,
    event_type: str,
    *,
    status: str = "",
    details: dict[str, str] | None = None,
    enabled: bool = True,
) -> None:
    """按需输出任务整体生命周期事件。"""
    if not enabled:
        return
    emit_task_run_event(
        logger,
        TaskRunEvent(
            event_type=event_type,
            status=status,
            details={} if details is None else details,
        ),
    )


def _build_dry_run_color_reader(
    dry_run_color: str,
    *,
    needs_color_reader: bool,
) -> PixelColorReader | None:
    """按任务需求创建 dry-run 固定取色 adapter。"""
    if not needs_color_reader:
        return None
    return DryRunPixelColorReader(Color.from_hex(dry_run_color))


def _build_dry_run_image_locator(
    dry_run_images: tuple[str, ...],
    *,
    needs_image_locator: bool,
) -> ScreenImageLocator | None:
    """按任务需求创建 dry-run 固定图像定位 adapter。"""
    if not needs_image_locator:
        return None
    matches = {
        ImageTemplate(path): ImageMatch(Rect(0, 0, 1, 1), confidence=1.0)
        for path in dry_run_images
    }
    return DryRunScreenImageLocator(matches)


def _build_dry_run_screen_state_reader(
    dry_run_screen_state: str,
    *,
    needs_screen_state_reader: bool,
) -> ScreenStateReader | None:
    """按任务需求创建 dry-run 固定界面状态 reader。"""
    if not needs_screen_state_reader:
        return None
    return DryRunScreenStateReader(dry_run_screen_state)
