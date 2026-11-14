"""为本地控制入口提供任务列表、详情与运行会话。

本 module 编排命名任务的同步或后台运行并收敛输出；不渲染页面、不解析协议、
不解释任务步骤。真实运行只交给原生窗口会话。
"""

from __future__ import annotations

import io
import threading
from collections import deque
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
from pathlib import Path

from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_SUFFIXES,
    PROJECT_ROOT,
    image_asset_root,
)
from game_automation.portable.application.runtime_ports import RuntimeFactory
from game_automation.portable.application.task_catalog import (
    TaskCatalog,
    TaskNotFoundError,
)
from game_automation.portable.application.task_details import (
    TaskDetailsResult,
    describe_task_details,
)
from game_automation.portable.application.task_discovery import TaskLoadError
from game_automation.portable.application.task_resources import (
    load_task_state_names,
    prepare_task_resources,
)
from game_automation.portable.application.task_run import run_task
from game_automation.portable.domain.task import FunctionTask
from game_automation.portable.engine.run_events import (
    TaskRunEvent,
    format_task_run_event,
)


@dataclass(frozen=True, slots=True)
class ControlResult:
    """表达同步任务运行的输出与结束原因。"""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    finish_reason: str = "completed"


@dataclass(frozen=True, slots=True)
class TaskRunStatus:
    running: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    finish_reason: str = "idle"
    events: tuple[TaskRunEvent, ...] = ()

    def __post_init__(self) -> None:
        """运行中的状态默认使用 running 作为结束原因占位。"""
        if self.running and self.finish_reason == "idle":
            object.__setattr__(self, "finish_reason", "running")


class _CancellationFlag:
    def __init__(self) -> None:
        """初始化线程安全取消标记。"""
        self._event = threading.Event()

    def cancel(self) -> None:
        """请求后台任务取消运行。"""
        self._event.set()

    def is_cancelled(self) -> bool:
        """返回后台任务是否已收到取消请求。"""
        return self._event.is_set()


class _ThreadSafeRunLog:
    def __init__(self) -> None:
        """初始化线程安全 stdout/stderr 缓冲。"""
        self._lock = threading.Lock()
        self._stdout = io.StringIO()
        self._stderr = io.StringIO()
        self._events: deque[TaskRunEvent] = deque(maxlen=2048)

    def stdout_writer(self):
        """返回用于重定向 stdout 的 writer。"""
        return _RunLogWriter(self.write_stdout)

    def stderr_writer(self):
        """返回用于重定向 stderr 的 writer。"""
        return _RunLogWriter(self.write_stderr)

    def log(self, message: str) -> None:
        """把运行诊断日志追加到 stdout。"""
        self.write_stdout(f"{message}\n")

    def log_event(self, event: TaskRunEvent) -> None:
        """记录结构化运行事件，并同步追加可读文本日志。"""
        with self._lock:
            self._events.append(
                replace(
                    event,
                    details={key: value[:4096] for key, value in event.details.items()},
                )
            )
            self._append(self._stdout, f"{format_task_run_event(event)}\n")

    def write_stdout(self, text: str) -> None:
        """追加一段 stdout 文本。"""
        with self._lock:
            self._append(self._stdout, text)

    def write_stderr(self, text: str) -> None:
        """追加一段 stderr 文本。"""
        with self._lock:
            self._append(self._stderr, text)

    @staticmethod
    def _append(stream: io.StringIO, text: str) -> None:
        """按块淘汰旧日志，限制内存并避免每次写入都复制整个缓冲。"""
        limit = 262144
        text = text[-limit:]
        if stream.tell() + len(text) > limit:
            keep = min(limit // 2, limit - len(text))
            tail = stream.getvalue()[-keep:] if keep else ""
            stream.seek(0)
            stream.write(tail)
            stream.truncate()
        stream.write(text)

    def snapshot(self) -> tuple[str, str]:
        """返回当前 stdout/stderr 文本快照。"""
        with self._lock:
            return self._stdout.getvalue(), self._stderr.getvalue()

    def snapshot_events(self) -> tuple[TaskRunEvent, ...]:
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

    def log_event(self, event: TaskRunEvent) -> None:
        """把结构化运行事件写入同步 stdout 捕获流。"""
        self._stream.write(f"{format_task_run_event(event)}\n")


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

    def snapshot(self) -> TaskRunStatus:
        """返回后台脚本当前状态快照。"""
        stdout, stderr = self.log.snapshot()
        events = self.log.snapshot_events()
        with self._lock:
            return TaskRunStatus(
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
        catalog: TaskCatalog | None = None,
        *,
        task_config_errors: tuple[TaskLoadError, ...] = (),
        project_root: Path = PROJECT_ROOT,
        real_runtime_factory: RuntimeFactory | None = None,
    ) -> None:
        """注入任务目录、项目路径和原生窗口运行时工厂。"""
        self._catalog = catalog if catalog is not None else TaskCatalog()
        self._task_config_errors = task_config_errors
        self._project_root = project_root
        self._real_runtime_factory = real_runtime_factory
        self._run_lock = threading.Lock()
        self._current_run: _BackgroundScriptRun | None = None
        self._run_thread: threading.Thread | None = None

    @property
    def workspace_path(self) -> Path:
        """返回此控制会话绑定的工作区，供入口明确展示任务来源。"""
        return self._project_root

    def list_tasks(self) -> tuple[str, ...]:
        """返回 UI 可展示的任务名称列表。"""
        return self._catalog.list_names()

    def list_task_config_errors(self) -> tuple[TaskLoadError, ...]:
        """返回任务加载时被隔离的配置错误。"""
        return self._task_config_errors

    def list_window_state_names(self) -> tuple[str, ...]:
        """列出窗口规则中的界面状态名称，配置不可用时返回空列表。"""
        return load_task_state_names(None, self._project_root) or ()

    def describe_task(self, name: str) -> TaskDetailsResult:
        """返回 UI 可展示的任务入口和依赖摘要。"""
        try:
            task = self._task_with_shared_resources(self._catalog.get(name))
        except TaskNotFoundError as exc:
            return TaskDetailsResult(exit_code=1, name=name, stderr=str(exc))
        except (LookupError, ValueError) as exc:
            return TaskDetailsResult(exit_code=2, name=name, stderr=f"{exc}\n")
        return describe_task_details(
            task,
            asset_root=self._image_asset_root(),
            supported_image_suffixes=IMAGE_ASSET_SUFFIXES,
            state_names=load_task_state_names(task, self._project_root),
        )

    def run_named_task(
        self,
        name: str,
        *,
        dry_run: bool,
        dry_run_color: str = "#000000",
        dry_run_screen_state: str = "未知",
        dry_run_images: tuple[str, ...] = (),
    ) -> ControlResult:
        """按名称运行任务，并捕获入口层可展示的输出。"""
        try:
            task = self._task_with_shared_resources(self._catalog.get(name))
        except TaskNotFoundError as exc:
            return ControlResult(
                exit_code=1, stderr=str(exc), finish_reason="task_not_found"
            )
        except (LookupError, ValueError) as exc:
            return ControlResult(
                exit_code=2,
                stderr=f"task resource configuration failed: {exc}\n",
                finish_reason="configuration_failed",
            )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = run_task(
                task,
                dry_run=dry_run,
                dry_run_color=dry_run_color,
                dry_run_images=dry_run_images if dry_run else (),
                dry_run_screen_state=dry_run_screen_state,
                real_runtime_factory=self._real_runtime_factory,
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

    def start_named_task(
        self,
        name: str,
        *,
        dry_run: bool,
        dry_run_color: str = "#000000",
        dry_run_screen_state: str = "未知",
        dry_run_images: tuple[str, ...] = (),
    ) -> TaskRunStatus:
        """启动一个后台任务运行会话。"""
        with self._run_lock:
            if self._current_run is not None and self._current_run.snapshot().running:
                current = self._current_run.snapshot()
                return TaskRunStatus(
                    running=current.running,
                    exit_code=current.exit_code,
                    stdout=current.stdout,
                    stderr=current.stderr + "task is already running\n",
                    finish_reason=current.finish_reason,
                    events=current.events,
                )
            try:
                task = self._task_with_shared_resources(self._catalog.get(name))
            except TaskNotFoundError as exc:
                return TaskRunStatus(
                    running=False,
                    exit_code=1,
                    stderr=str(exc),
                    finish_reason="task_not_found",
                )
            except (LookupError, ValueError) as exc:
                return TaskRunStatus(
                    running=False,
                    exit_code=2,
                    stderr=f"task resource configuration failed: {exc}\n",
                    finish_reason="configuration_failed",
                )

            session = _BackgroundScriptRun()
            self._current_run = session
            thread = threading.Thread(
                target=self._run_task_session,
                args=(
                    task,
                    dry_run,
                    dry_run_color,
                    dry_run_screen_state,
                    dry_run_images if dry_run else (),
                    session,
                ),
                daemon=True,
            )
            self._run_thread = thread
            thread.start()
            return session.snapshot()

    def current_task_run(self) -> TaskRunStatus:
        """返回当前后台任务运行状态。"""
        with self._run_lock:
            if self._current_run is None:
                return TaskRunStatus(running=False)
            return self._current_run.snapshot()

    def stop_running_task(self) -> TaskRunStatus:
        """请求停止当前后台任务运行。"""
        with self._run_lock:
            if self._current_run is None:
                return TaskRunStatus(
                    running=False, exit_code=0, stderr="no task is running\n"
                )
            self._current_run.cancellation.cancel()
            return self._current_run.snapshot()

    def wait_for_task_stop(self, timeout: float | None = None) -> bool:
        """等待后台线程真正退出，供宿主在取消后有序回收进程。"""
        with self._run_lock:
            thread = self._run_thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def _run_task_session(
        self,
        task: FunctionTask,
        dry_run: bool,
        dry_run_color: str,
        dry_run_screen_state: str,
        dry_run_images: tuple[str, ...],
        session: _BackgroundScriptRun,
    ) -> None:
        """在后台线程中运行任务并写入会话状态。"""
        exit_code, finish_reason = 1, "failed"
        try:
            with (
                redirect_stdout(session.log.stdout_writer()),
                redirect_stderr(session.log.stderr_writer()),
            ):
                result = run_task(
                    task,
                    dry_run=dry_run,
                    dry_run_color=dry_run_color,
                    dry_run_images=dry_run_images,
                    dry_run_screen_state=dry_run_screen_state,
                    real_runtime_factory=self._real_runtime_factory,
                    cancellation_token=session.cancellation,
                    logger=session.log,
                    emit_step_events=True,
                )
            exit_code, finish_reason = result.exit_code, result.finish_reason
            if result.error_message is not None:
                session.log.write_stderr(f"{result.error_message}\n")
        except Exception as exc:
            message = f"unexpected task run failure: {type(exc).__name__}: {exc}"
            session.log.write_stderr(f"{message}\n")
            session.log.log_event(
                TaskRunEvent(
                    event_type="run_finished",
                    status="failed",
                    details={"exit_code": "1", "error": message},
                )
            )
        finally:
            # 会话状态由本层持有，即使用例漏掉异常归一化也必须释放运行槽位。
            session.finish(exit_code, finish_reason)

    def _image_asset_root(self) -> Path:
        """返回本地 UI 允许读取模板图片的项目内目录。"""
        return image_asset_root(self._project_root)

    def _task_with_shared_resources(self, task: FunctionTask) -> FunctionTask:
        """按任务需要合并窗口规则里的共享搜索资源。"""
        return prepare_task_resources(task, self._project_root)
