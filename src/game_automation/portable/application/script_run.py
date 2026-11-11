"""编排单次脚本运行的应用 module。

本 module 负责选择 dry-run 或真实 adapter、补齐脚本所需端口、调用 runner，
并把运行配置、setup 和超时错误归一化；它不做脚本注册表查找，也不打印 CLI 输出。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from contextlib import ExitStack
from time import monotonic

from game_automation.portable.adapters.dry_run import (
    DryRunInputDevice,
    DryRunPixelColorReader,
    DryRunScreenImageLocator,
    DryRunScreenStateReader,
)
from game_automation.portable.application.runtime_ports import RuntimeFactory
from game_automation.portable.application.ports import ApplicationActivator, ApplicationWindowController
from game_automation.portable.application.script_dependencies import validate_script_resource_references
from game_automation.portable.domain import AreaWindow, Color, ImageMatch, ImageTemplate, Rect, Script
from game_automation.portable.engine.ports import (
    CancellationToken,
    InputDevice,
    PixelColorReader,
    RunLogger,
    ScreenImageLocator,
    ScreenStateReader,
    RuntimeControl,
)
from game_automation.portable.engine.run_events import ScriptRunEvent, emit_script_run_event
from game_automation.portable.engine.runner import ScriptCancelledError, ScriptRunner
from game_automation.portable.engine.script_requirements import inspect_script_requirements

InputDeviceFactory = Callable[[], InputDevice]
PixelColorReaderFactory = Callable[[], PixelColorReader]
ScreenImageLocatorFactory = Callable[[], ScreenImageLocator]
ScreenStateReaderFactory = Callable[[], ScreenStateReader]
ApplicationActivatorFactory = Callable[[], ApplicationActivator]
ApplicationWindowControllerFactory = Callable[[], ApplicationWindowController]


@dataclass(frozen=True, slots=True)
class ScriptRunResult:
    exit_code: int
    error_message: str | None = None
    finish_reason: str = "completed"


def run_script(
    script: Script,
    *,
    dry_run: bool,
    dry_run_color: str = "#000000",
    dry_run_images: tuple[str, ...] = (),
    dry_run_screen_state: str = "未知",
    target_application: str | None = None,
    target_window_title: str | None = None,
    real_application_activator_factory: ApplicationActivatorFactory | None = None,
    real_application_window_controller_factory: ApplicationWindowControllerFactory | None = None,
    real_runtime_factory: RuntimeFactory | None = None,
    real_device_factory: InputDeviceFactory | None = None,
    real_color_reader_factory: PixelColorReaderFactory | None = None,
    real_image_locator_factory: ScreenImageLocatorFactory | None = None,
    real_screen_state_reader_factory: ScreenStateReaderFactory | None = None,
    cancellation_token: CancellationToken | None = None,
    logger: RunLogger | None = None,
    emit_step_events: bool = False,
) -> ScriptRunResult:
    """运行一份已解析脚本，并返回入口层可直接映射的结果。"""
    if emit_step_events:
        _emit_run_lifecycle_event(
            logger,
            "run_started",
            details={"script": script.name, "dry_run": str(dry_run)},
        )
    stack = ExitStack()
    runtime_control = None
    stage = "setup"
    result = ScriptRunResult(1, "script run did not finish", "failed")
    try:
        validate_script_resource_references(script)
        native = not dry_run and script.target is not None and script.target.uses_native_window
        if native:
            if target_application is not None or target_window_title is not None:
                raise ValueError(f"{script.target.backend} uses the script target; CLI target overrides are unsupported")
            if real_runtime_factory is None:
                raise RuntimeError(f"{script.target.backend} runtime factory is required; desktop fallback is disabled")
            if logger is not None:
                logger.log(f"runtime selected backend={script.target.backend} target={script.target.application!r} title={script.target.window_title!r}")
            requirements = inspect_script_requirements(script)
            ports = stack.enter_context(real_runtime_factory.open(
                script.target, requirements, cancellation_token, logger))
            for needed, port, name in (
                (True, ports.device, "device"),
                (requirements.needs_color_reader, ports.color_reader, "color reader"),
                (requirements.needs_image_locator, ports.image_locator, "image locator"),
                (requirements.needs_screen_state_reader, ports.screen_state_reader, "screen state reader"),
            ):
                if needed and port is None:
                    raise RuntimeError(f"{script.target.backend} runtime did not supply required {name}")
            runtime_control = ports.control
            prepared_script = replace(script, window=ports.window)
            real_device_factory = lambda: ports.device
            real_color_reader_factory = lambda: ports.color_reader
            real_image_locator_factory = lambda: ports.image_locator
            real_screen_state_reader_factory = lambda: ports.screen_state_reader
        else:
            prepared_script = _prepare_target_environment(
                script, dry_run=dry_run, target_application=target_application,
                target_window_title=target_window_title,
                real_application_activator_factory=real_application_activator_factory,
                real_application_window_controller_factory=real_application_window_controller_factory)
        runner = _build_runner(
            prepared_script, dry_run=dry_run, dry_run_color=dry_run_color,
            dry_run_images=dry_run_images, dry_run_screen_state=dry_run_screen_state,
            real_device_factory=real_device_factory,
            real_color_reader_factory=real_color_reader_factory,
            real_image_locator_factory=real_image_locator_factory,
            real_screen_state_reader_factory=real_screen_state_reader_factory,
            cancellation_token=cancellation_token, logger=logger, emit_step_events=emit_step_events,
            runtime_control=runtime_control)
        stage = "run"
        execution_result = runner.run(prepared_script)
        result = ScriptRunResult(0, finish_reason=execution_result.finish_reason)
        execution_message = execution_result.message
    except ScriptCancelledError as exc:
        result = ScriptRunResult(130, str(exc), "cancelled")
    except Exception as exc:
        if stage == "setup":
            reason = "configuration_failed" if isinstance(exc, (LookupError, ValueError)) else "setup_failed"
            result = ScriptRunResult(2 if reason == "configuration_failed" else 1,
                                     f"script run {'configuration' if reason == 'configuration_failed' else 'setup'} failed: {exc}", reason)
        elif isinstance(exc, TimeoutError):
            result = ScriptRunResult(1, f"script run timed out: {exc}", "timed_out")
        else:
            result = ScriptRunResult(1, f"script run failed: {exc}", "failed")
    finally:
        try:
            stack.close()
        except Exception as exc:
            message = f"runtime cleanup failed: {exc}"
            if logger is not None:
                logger.log(message)
            if result.finish_reason == "cancelled":
                result = replace(result, error_message=f"{result.error_message}; {message}")
            else:
                result = ScriptRunResult(1, message, "cleanup_failed")
    # 停流可能等待回调屏障；此期间到达的取消仍高于完成和清理失败。
    if cancellation_token is not None and cancellation_token.is_cancelled():
        result = ScriptRunResult(130, result.error_message or "script run cancelled", "cancelled")
    details = {"exit_code": str(result.exit_code)}
    if result.exit_code == 0 and result.finish_reason != "completed":
        details["reason"] = execution_message or ""
    if result.error_message is not None:
        details["error"] = result.error_message
    _emit_run_lifecycle_event(logger, "run_finished", status=result.finish_reason,
                              details=details, enabled=emit_step_events)
    return result


def _prepare_target_environment(
    script: Script,
    *,
    dry_run: bool,
    target_application: str | None,
    target_window_title: str | None,
    real_application_activator_factory: ApplicationActivatorFactory | None,
    real_application_window_controller_factory: ApplicationWindowControllerFactory | None,
) -> Script:
    """在真实 runner 创建前激活应用、选窗并返回本轮脚本副本。"""
    if dry_run:
        return script
    declared_target = script.target if target_application is None and target_window_title is None else None
    if declared_target is not None:
        target_application = declared_target.application
        target_window_title = declared_target.window_title
    if target_window_title is not None and target_application is None:
        raise ValueError("target window title requires target application")
    if target_application is None:
        return script
    normalized_application = target_application.strip()
    if not normalized_application:
        raise ValueError("target application must not be empty")
    if real_application_activator_factory is None:
        raise RuntimeError("real application activator factory is required")
    real_application_activator_factory().activate(normalized_application)
    if target_window_title is None:
        return script
    normalized_title = target_window_title.strip()
    if not normalized_title:
        raise ValueError("target window title must not be empty")
    if real_application_window_controller_factory is None:
        raise RuntimeError("real application window controller factory is required")
    focused_window = real_application_window_controller_factory().focus_window(
        normalized_application,
        normalized_title,
    )
    if declared_target is not None and (focused_window.rect.width,focused_window.rect.height) != (declared_target.width,declared_target.height):
        raise ValueError('目标窗口尺寸与脚本素材不符，请恢复窗口尺寸后重试')
    return replace(script, window=AreaWindow(focused_window.rect))


def _build_runner(
    script: Script,
    *,
    dry_run: bool,
    dry_run_color: str,
    dry_run_images: tuple[str, ...],
    dry_run_screen_state: str,
    real_device_factory: InputDeviceFactory | None,
    real_color_reader_factory: PixelColorReaderFactory | None,
    real_image_locator_factory: ScreenImageLocatorFactory | None,
    real_screen_state_reader_factory: ScreenStateReaderFactory | None,
    cancellation_token: CancellationToken | None,
    logger: RunLogger | None,
    emit_step_events: bool,
    runtime_control: RuntimeControl | None = None,
) -> ScriptRunner:
    """按脚本运行模式和端口需求组装 runner。"""
    requirements = inspect_script_requirements(script)
    if dry_run:
        device = DryRunInputDevice()
        return ScriptRunner(
            device=device,
            clock=device.clock,
            color_reader=_build_dry_run_color_reader(
                dry_run_color,
                needs_color_reader=requirements.needs_color_reader,
            ),
            image_locator=_build_dry_run_image_locator(
                dry_run_images,
                needs_image_locator=requirements.needs_image_locator,
            ),
            screen_state_reader=_build_dry_run_screen_state_reader(
                dry_run_screen_state,
                needs_screen_state_reader=requirements.needs_screen_state_reader,
            ),
            cancellation_token=cancellation_token,
            logger=logger,
            emit_step_events=emit_step_events,
        )

    device = _build_real_device(real_device_factory)
    if cancellation_token is not None:
        device = _CancellableInputDevice(device, cancellation_token)
    return ScriptRunner(
        device=device,
        clock=monotonic if runtime_control is None else runtime_control.task_time,
        runtime_control=runtime_control,
        color_reader=_build_real_color_reader(
            needs_color_reader=requirements.needs_color_reader,
            real_color_reader_factory=real_color_reader_factory,
        ),
        image_locator=_build_real_image_locator(
            needs_image_locator=requirements.needs_image_locator,
            real_image_locator_factory=real_image_locator_factory,
        ),
        screen_state_reader=_build_real_screen_state_reader(
            needs_screen_state_reader=requirements.needs_screen_state_reader,
            real_screen_state_reader_factory=real_screen_state_reader_factory,
        ),
        cancellation_token=cancellation_token,
        logger=logger,
        emit_step_events=emit_step_events,
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
                raise ScriptCancelledError("script run cancelled")
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
    """按需输出脚本整体生命周期事件。"""
    if not enabled:
        return
    emit_script_run_event(
        logger,
        ScriptRunEvent(
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
    """按脚本需求创建 dry-run 固定取色 adapter。"""
    if not needs_color_reader:
        return None
    return DryRunPixelColorReader(Color.from_hex(dry_run_color))


def _build_real_device(real_device_factory: InputDeviceFactory | None) -> InputDevice:
    """通过平台层注入的工厂创建真实输入 adapter。"""
    if real_device_factory is None:
        raise RuntimeError("real input device factory is required")
    return real_device_factory()


def _build_dry_run_image_locator(
    dry_run_images: tuple[str, ...],
    *,
    needs_image_locator: bool,
) -> ScreenImageLocator | None:
    """按脚本需求创建 dry-run 固定图像定位 adapter。"""
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
    """按脚本需求创建 dry-run 固定界面状态 reader。"""
    if not needs_screen_state_reader:
        return None
    return DryRunScreenStateReader(dry_run_screen_state)


def _build_real_color_reader(
    *,
    needs_color_reader: bool,
    real_color_reader_factory: PixelColorReaderFactory | None,
) -> PixelColorReader | None:
    """按脚本需求通过平台层注入的工厂创建真实取色 adapter。"""
    if not needs_color_reader:
        return None
    if real_color_reader_factory is None:
        raise RuntimeError("real color reader factory is required")
    return real_color_reader_factory()


def _build_real_image_locator(
    *,
    needs_image_locator: bool,
    real_image_locator_factory: ScreenImageLocatorFactory | None,
) -> ScreenImageLocator | None:
    """按脚本需求通过平台层注入的工厂创建真实图像定位 adapter。"""
    if not needs_image_locator:
        return None
    if real_image_locator_factory is None:
        raise RuntimeError("real image locator factory is required")
    return real_image_locator_factory()


def _build_real_screen_state_reader(
    *,
    needs_screen_state_reader: bool,
    real_screen_state_reader_factory: ScreenStateReaderFactory | None,
) -> ScreenStateReader | None:
    """按脚本需求通过平台层注入的工厂创建真实界面状态 reader。"""
    if not needs_screen_state_reader:
        return None
    if real_screen_state_reader_factory is None:
        raise RuntimeError("real screen state reader factory is required")
    return real_screen_state_reader_factory()
