"""为本地控制入口提供脚本列表、详情与运行会话。

本 module 编排命名脚本的同步或后台运行并收敛输出；不渲染页面、不解析 HTTP、
不解释脚本步骤。界面状态通过独立 reader 实时读取，不持有后台探测缓存。
"""

from __future__ import annotations

import io
import threading
from contextlib import redirect_stderr, redirect_stdout
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.config_script_loader import ScriptConfigError
from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_SUFFIXES,
    PROJECT_ROOT,
    image_asset_root,
    screen_state_config_path,
)
from game_automation.portable.application.screen_state_config import load_screen_state_names
from game_automation.portable.application.screen_state_reader import (
    ProjectScreenStateReader,
    ScreenImageBatchLocatorFactory,
)
from game_automation.portable.application.script_details import ScriptDetailsResult, describe_script_details
from game_automation.portable.application.script_resources import (
    load_shared_script_resources,
    script_with_shared_resources,
)
from game_automation.portable.application.script_run import (
    InputDeviceFactory,
    PixelColorReaderFactory,
    ScreenImageLocatorFactory,
    run_script,
)
from game_automation.portable.domain import Script
from game_automation.portable.engine.ports import ScreenStateReader
from game_automation.portable.engine.run_events import ScriptRunEvent, format_script_run_event
from game_automation.portable.scripts_manager import DEFAULT_SCRIPT_CATALOG
from game_automation.portable.scripts_manager.catalog import ScriptCatalog, ScriptNotFoundError


@dataclass(frozen=True, slots=True)
class ControlResult:
    """表达同步脚本运行的输出与结束原因。"""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    finish_reason: str = "completed"


@dataclass(frozen=True, slots=True)
class ScriptRunStatus:
    running: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    finish_reason: str = "idle"
    events: tuple[ScriptRunEvent, ...] = ()

    def __post_init__(self) -> None:
        """运行中的状态默认使用 running 作为结束原因占位。"""
        if self.running and self.finish_reason == "idle":
            object.__setattr__(self, "finish_reason", "running")


class _CancellationFlag:
    def __init__(self) -> None:
        """初始化线程安全取消标记。"""
        self._event = threading.Event()

    def cancel(self) -> None:
        """请求后台脚本取消运行。"""
        self._event.set()

    def is_cancelled(self) -> bool:
        """返回后台脚本是否已收到取消请求。"""
        return self._event.is_set()


class _ThreadSafeRunLog:
    def __init__(self) -> None:
        """初始化线程安全 stdout/stderr 缓冲。"""
        self._lock = threading.Lock()
        self._stdout = io.StringIO()
        self._stderr = io.StringIO()
        self._events: list[ScriptRunEvent] = []

    def stdout_writer(self):
        """返回用于重定向 stdout 的 writer。"""
        return _RunLogWriter(self.write_stdout)

    def stderr_writer(self):
        """返回用于重定向 stderr 的 writer。"""
        return _RunLogWriter(self.write_stderr)

    def log(self, message: str) -> None:
        """把运行诊断日志追加到 stdout。"""
        self.write_stdout(f"{message}\n")

    def log_event(self, event: ScriptRunEvent) -> None:
        """记录结构化运行事件，并同步追加可读文本日志。"""
        with self._lock:
            self._events.append(event)
            self._stdout.write(f"{format_script_run_event(event)}\n")

    def write_stdout(self, text: str) -> None:
        """追加一段 stdout 文本。"""
        with self._lock:
            self._stdout.write(text)

    def write_stderr(self, text: str) -> None:
        """追加一段 stderr 文本。"""
        with self._lock:
            self._stderr.write(text)

    def snapshot(self) -> tuple[str, str]:
        """返回当前 stdout/stderr 文本快照。"""
        with self._lock:
            return self._stdout.getvalue(), self._stderr.getvalue()

    def snapshot_events(self) -> tuple[ScriptRunEvent, ...]:
        """返回当前结构化运行事件快照。"""
        with self._lock:
            return tuple(self._events)


class _RunLogWriter:
    def __init__(self, write_text: Callable[[str], None]) -> None:
        """保存日志写入函数。"""
        self._write_text = write_text

    def write(self, text: str) -> int:
        """兼容 redirect_stdout 所需的 writer interface。"""
        self._write_text(text)
        return len(text)

    def flush(self) -> None:
        """兼容 writer interface，线程安全缓冲无需额外 flush。"""


class _StringRunLogger:
    def __init__(self, stream: io.StringIO) -> None:
        """保存同步运行时要写入的文本流。"""
        self._stream = stream

    def log(self, message: str) -> None:
        """把运行诊断日志写入同步 stdout 捕获流。"""
        self._stream.write(f"{message}\n")

    def log_event(self, event: ScriptRunEvent) -> None:
        """把结构化运行事件写入同步 stdout 捕获流。"""
        self._stream.write(f"{format_script_run_event(event)}\n")


class _BackgroundScriptRun:
    def __init__(self) -> None:
        """初始化后台脚本会话状态。"""
        self.cancellation = _CancellationFlag()
        self.log = _ThreadSafeRunLog()
        self._lock = threading.Lock()
        self._running = True
        self._exit_code: int | None = None
        self._finish_reason = "running"

    def finish(self, exit_code: int, finish_reason: str) -> None:
        """记录后台脚本结束状态。"""
        with self._lock:
            self._running = False
            self._exit_code = exit_code
            self._finish_reason = finish_reason

    def snapshot(self) -> ScriptRunStatus:
        """返回后台脚本当前状态快照。"""
        stdout, stderr = self.log.snapshot()
        events = self.log.snapshot_events()
        with self._lock:
            return ScriptRunStatus(
                running=self._running,
                exit_code=self._exit_code,
                stdout=stdout,
                stderr=stderr,
                finish_reason="running" if self._running else self._finish_reason,
                events=events,
            )


class LocalControlApplication:
    def __init__(
        self,
        catalog: ScriptCatalog = DEFAULT_SCRIPT_CATALOG,
        *,
        script_config_errors: tuple[ScriptConfigError, ...] = (),
        project_root: Path = PROJECT_ROOT,
        real_device_factory: InputDeviceFactory | None = None,
        real_color_reader_factory: PixelColorReaderFactory | None = None,
        real_image_locator_factory: ScreenImageLocatorFactory | None = None,
        real_image_batch_locator_factory: ScreenImageBatchLocatorFactory | None = None,
    ) -> None:
        """注入脚本目录、项目路径和运行所需的外部能力工厂。"""
        self._catalog = catalog
        self._script_config_errors = script_config_errors
        self._project_root = project_root
        self._real_device_factory = real_device_factory
        self._real_color_reader_factory = real_color_reader_factory
        self._real_image_locator_factory = real_image_locator_factory
        self._real_image_batch_locator_factory = real_image_batch_locator_factory
        self._run_lock = threading.Lock()
        self._current_run: _BackgroundScriptRun | None = None

    @property
    def workspace_path(self) -> Path:
        """返回此控制会话绑定的工作区，供入口明确展示任务来源。"""
        return self._project_root

    def list_scripts(self) -> tuple[str, ...]:
        """返回 UI 可展示的脚本名称列表。"""
        return self._catalog.list_names()

    def list_script_config_errors(self) -> tuple[ScriptConfigError, ...]:
        """返回文件脚本加载时被隔离的配置错误。"""
        return self._script_config_errors

    def list_screen_state_names(self) -> tuple[str, ...]:
        """列出状态配置中的界面状态名称，配置不可用时返回空列表。"""
        try:
            names = load_screen_state_names(screen_state_config_path(self._project_root))
        except ValueError:
            return ()
        return () if names is None else names

    def describe_script(self, name: str) -> ScriptDetailsResult:
        """返回 UI 可展示的脚本步骤和依赖摘要。"""
        try:
            script = self._script_with_shared_resources(self._catalog.get(name))
        except ScriptNotFoundError as exc:
            return ScriptDetailsResult(exit_code=1, name=name, stderr=str(exc))
        except (LookupError, ValueError) as exc:
            return ScriptDetailsResult(exit_code=2, name=name, stderr=f"{exc}\n")
        return describe_script_details(
            script,
            asset_root=self._image_asset_root(),
            supported_image_suffixes=IMAGE_ASSET_SUFFIXES,
            state_names=self._configured_screen_state_names_for_readiness(),
        )

    def run_named_script(
        self,
        name: str,
        *,
        dry_run: bool,
        dry_run_color: str = "#000000",
        dry_run_screen_state: str = "未知",
        dry_run_images: tuple[str, ...] = (),
    ) -> ControlResult:
        """按名称运行脚本，并捕获入口层可展示的输出。"""
        try:
            script = self._script_with_shared_resources(self._catalog.get(name))
        except ScriptNotFoundError as exc:
            return ControlResult(exit_code=1, stderr=str(exc), finish_reason="script_not_found")
        except (LookupError, ValueError) as exc:
            return ControlResult(
                exit_code=2,
                stderr=f"script resource configuration failed: {exc}\n",
                finish_reason="configuration_failed",
            )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = run_script(
                script,
                dry_run=dry_run,
                dry_run_color=dry_run_color,
                dry_run_images=dry_run_images if dry_run else (),
                dry_run_screen_state=dry_run_screen_state,
                real_device_factory=self._real_device_factory,
                real_color_reader_factory=self._real_color_reader_factory,
                real_image_locator_factory=self._real_image_locator_factory,
                real_screen_state_reader_factory=self.build_screen_state_reader,
                logger=_StringRunLogger(stdout),
            )

        if result.error_message is not None:
            stderr.write(result.error_message)
            stderr.write("\n")
        return ControlResult(
            exit_code=result.exit_code,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
            finish_reason=result.finish_reason,
        )

    def start_named_script(
        self,
        name: str,
        *,
        dry_run: bool,
        dry_run_color: str = "#000000",
        dry_run_screen_state: str = "未知",
        dry_run_images: tuple[str, ...] = (),
    ) -> ScriptRunStatus:
        """启动一个后台脚本运行会话。"""
        with self._run_lock:
            if self._current_run is not None and self._current_run.snapshot().running:
                current = self._current_run.snapshot()
                return ScriptRunStatus(
                    running=current.running,
                    exit_code=current.exit_code,
                    stdout=current.stdout,
                    stderr=current.stderr + "script is already running\n",
                    finish_reason=current.finish_reason,
                    events=current.events,
                )
            try:
                script = self._script_with_shared_resources(self._catalog.get(name))
            except ScriptNotFoundError as exc:
                return ScriptRunStatus(
                    running=False,
                    exit_code=1,
                    stderr=str(exc),
                    finish_reason="script_not_found",
                )
            except (LookupError, ValueError) as exc:
                return ScriptRunStatus(
                    running=False,
                    exit_code=2,
                    stderr=f"script resource configuration failed: {exc}\n",
                    finish_reason="configuration_failed",
                )

            session = _BackgroundScriptRun()
            self._current_run = session
            thread = threading.Thread(
                target=self._run_script_session,
                args=(
                    script,
                    dry_run,
                    dry_run_color,
                    dry_run_screen_state,
                    dry_run_images if dry_run else (),
                    session,
                ),
                daemon=True,
            )
            thread.start()
            return session.snapshot()

    def current_script_run(self) -> ScriptRunStatus:
        """返回当前后台脚本运行状态。"""
        with self._run_lock:
            if self._current_run is None:
                return ScriptRunStatus(running=False)
            return self._current_run.snapshot()

    def stop_running_script(self) -> ScriptRunStatus:
        """请求停止当前后台脚本运行。"""
        with self._run_lock:
            if self._current_run is None:
                return ScriptRunStatus(running=False, exit_code=0, stderr="no script is running\n")
            self._current_run.cancellation.cancel()
            return self._current_run.snapshot()

    def _run_script_session(
        self,
        script: Script,
        dry_run: bool,
        dry_run_color: str,
        dry_run_screen_state: str,
        dry_run_images: tuple[str, ...],
        session: _BackgroundScriptRun,
    ) -> None:
        """在后台线程中运行脚本并写入会话状态。"""
        with redirect_stdout(session.log.stdout_writer()), redirect_stderr(session.log.stderr_writer()):
            result = run_script(
                script,
                dry_run=dry_run,
                dry_run_color=dry_run_color,
                dry_run_images=dry_run_images,
                dry_run_screen_state=dry_run_screen_state,
                real_device_factory=self._real_device_factory,
                real_color_reader_factory=self._real_color_reader_factory,
                real_image_locator_factory=self._real_image_locator_factory,
                real_screen_state_reader_factory=self.build_screen_state_reader,
                cancellation_token=session.cancellation,
                logger=session.log,
                emit_step_events=True,
            )
        if result.error_message is not None:
            session.log.write_stderr(f"{result.error_message}\n")
        session.finish(result.exit_code, result.finish_reason)

    def _image_asset_root(self) -> Path:
        """返回本地 UI 允许读取模板图片的项目内目录。"""
        return image_asset_root(self._project_root)

    def _configured_screen_state_names_for_readiness(self) -> tuple[str, ...] | None:
        """读取状态名用于详情检查，配置不可用时返回 None。"""
        try:
            return load_screen_state_names(screen_state_config_path(self._project_root))
        except ValueError:
            return None

    def _script_with_shared_resources(self, script: Script) -> Script:
        """把状态配置里的共享搜索资源合并进脚本资源目录。"""
        return script_with_shared_resources(script, self._shared_script_resources())

    def _shared_script_resources(self):
        """读取本地状态配置中可供脚本复用的资源目录。"""
        return load_shared_script_resources(self._project_root)

    def build_screen_state_reader(self) -> ScreenStateReader:
        """创建按需读取最新配置和画面的状态 reader。"""
        return ProjectScreenStateReader(
            project_root=self._project_root,
            real_image_locator_factory=self._real_image_locator_factory,
            real_image_batch_locator_factory=self._real_image_batch_locator_factory,
        )
