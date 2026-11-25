"""为本地控制入口提供任务列表、详情与运行会话。

本 module 编排命名任务的同步或后台运行并收敛输出；不渲染页面、不解析协议、
不解释任务步骤。真实运行只交给原生窗口会话。
"""

from __future__ import annotations

import io
import threading
from collections import deque
from collections.abc import Callable
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
from pathlib import Path

from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_SUFFIXES,
    PROJECT_ROOT,
    image_asset_root,
)
from game_automation.portable.application.project_run_plan import (
    SavedPlanEntry,
    SavedRunPlan,
    load_saved_run_plan,
    save_run_plan,
    saved_run_plan_data,
)
from game_automation.portable.application.run_archive import RunArchive
from game_automation.portable.application.run_plan import (
    TaskPlanItem,
    TaskPlanRunResult,
    run_task_plan,
)
from game_automation.portable.application.runtime_ports import (
    RuntimeFactory,
    RuntimeWindowIdentity,
)
from game_automation.portable.application.task_catalog import (
    TaskCatalog,
    TaskNotFoundError,
)
from game_automation.portable.application.task_dependencies import (
    validate_task_resource_references,
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
from game_automation.portable.domain.task import FunctionTask, TaskTarget
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
    artifacts_path: str = ""

    def __post_init__(self) -> None:
        """运行中的状态默认使用 running 作为结束原因占位。"""
        if self.running and self.finish_reason == "idle":
            object.__setattr__(self, "finish_reason", "running")


@dataclass(frozen=True, slots=True)
class CompanionSelection:
    """提供本次运行已验证的窗口身份或空闲时的目标声明。"""

    running: bool
    target: TaskTarget | None = None
    window: RuntimeWindowIdentity | None = None


class _TrackedRuntimeFactory:
    """将真实会话身份交给运行状态，关闭后撤销该身份。"""

    def __init__(self, factory, session):
        """借用底层工厂及本次运行状态。"""
        self._factory, self._session = factory, session

    @contextmanager
    def open(self, target, requirements, cancellation, logger):
        """只在底层独占会话实际打开期间发布窗口身份。"""
        with self._factory.open(target, requirements, cancellation, logger) as ports:
            self._session.set_window(ports.window_identity)
            try:
                yield ports
            finally:
                self._session.set_window(None)


class _CancellationFlag:
    def __init__(self) -> None:
        """初始化线程安全取消标记。"""
        self._event = threading.Event()

    def cancel(self) -> None:
        """持久设置线程安全停止标记，执行线程在后续取消检查点读取它。"""
        self._event.set()

    def is_cancelled(self) -> bool:
        """读取停止请求标记，返回真值仅表示已请求取消。"""
        return self._event.is_set()

    def wait(self, seconds: float) -> bool:
        """等待指定秒数，收到取消立即返回未完成。"""
        return not self._event.wait(seconds)


class _ThreadSafeRunLog:
    def __init__(self, archive: RunArchive | None = None) -> None:
        """初始化线程安全 stdout/stderr 缓冲。"""
        self._lock = threading.Lock()
        self._stdout = io.StringIO()
        self._stderr = io.StringIO()
        self._events: deque[TaskRunEvent] = deque(maxlen=2048)
        self._archive = archive

    def stdout_writer(self):
        """创建接入当前会话 stdout 缓冲与归档的写入器，供 redirect_stdout 使用。"""
        return _RunLogWriter(self.write_stdout)

    def stderr_writer(self):
        """创建接入当前会话 stderr 缓冲与归档的写入器，供 redirect_stderr 使用。"""
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
            text = f"{format_task_run_event(event)}\n"
            self._persist("stdout", text)
            self._append(self._stdout, text)

    def write_stdout(self, text: str) -> None:
        """在日志锁内同时写 stdout 归档和有界界面缓冲。"""
        with self._lock:
            self._persist("stdout", text)
            self._append(self._stdout, text)

    def write_stderr(self, text: str) -> None:
        """在日志锁内同时写 stderr 归档和有界界面缓冲。"""
        with self._lock:
            self._persist("stderr", text)
            self._append(self._stderr, text)

    def _persist(self, channel: str, text: str) -> None:
        """把完整文本交给当前运行归档。"""
        if self._archive is None:
            return
        self._archive.write(channel, text)

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
        """借用调用方的追加函数，将标准流写入转交给所属会话。"""
        self._write_text = write_text

    def write(self, text: str) -> int:
        """兼容 redirect_stdout 所需的 writer interface。"""
        self._write_text(text)
        return len(text)

    def flush(self) -> None:
        """兼容 writer interface，线程安全缓冲无需额外 flush。"""


class _StringRunLogger:
    def __init__(self, stream: io.StringIO) -> None:
        """借用调用方的内存流，同步诊断与任务输出汇入同一捕获结果。"""
        self._stream = stream

    def log(self, message: str) -> None:
        """把运行诊断日志写入同步 stdout 捕获流。"""
        self._stream.write(f"{message}\n")

    def log_event(self, event: TaskRunEvent) -> None:
        """把结构化运行事件写入同步 stdout 捕获流。"""
        self._stream.write(f"{format_task_run_event(event)}\n")


class _BackgroundScriptRun:
    def __init__(self, archive: RunArchive | None = None) -> None:
        """为本次运行创建独立取消标记和日志缓冲，并以运行中状态等待线程结算。"""
        self.cancellation = _CancellationFlag()
        self.archive = archive
        self.log = _ThreadSafeRunLog(archive)
        self._lock = threading.Lock()
        self._running = True
        self._exit_code: int | None = None
        self._finish_reason = "running"
        self._window: RuntimeWindowIdentity | None = None
        self._last_window: RuntimeWindowIdentity | None = None

    def set_window(self, window: RuntimeWindowIdentity | None) -> None:
        """在会话开启和关闭边界发布不可变窗口身份。"""
        with self._lock:
            self._window = window
            if window is not None:
                self._last_window = window

    def companion_selection(self) -> CompanionSelection:
        """运行间隙沿用本次已验证身份，新运行拥有独立状态。"""
        with self._lock:
            return CompanionSelection(
                self._running, window=self._window or self._last_window
            )

    def finish(self, exit_code: int, finish_reason: str) -> None:
        """先结算持久记录，再在状态锁内发布退出码与结束原因。"""
        if self.archive is not None:
            self.archive.finish(exit_code, finish_reason)
        with self._lock:
            self._running = False
            self._exit_code = exit_code
            self._finish_reason = finish_reason

    def snapshot(self) -> TaskRunStatus:
        """组合当前日志、事件和归档警告，运行期间统一返回 running 结束原因。"""
        stdout, stderr = self.log.snapshot()
        events = self.log.snapshot_events()
        if self.archive is not None and self.archive.warnings:
            stderr += "\n" + "\n".join(self.archive.warnings)
        with self._lock:
            return TaskRunStatus(
                running=self._running,
                exit_code=self._exit_code,
                stdout=stdout,
                stderr=stderr,
                finish_reason="running" if self._running else self._finish_reason,
                events=events,
                artifacts_path=str(self.archive.path)
                if self.archive and self.archive.path
                else "",
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
        """按 catalog 的注册顺序提供任务名，供界面展示当前工作区的有效任务。"""
        return self._catalog.list_names()

    def list_task_config_errors(self) -> tuple[TaskLoadError, ...]:
        """返回任务加载时被隔离的配置错误。"""
        return self._task_config_errors

    def list_window_state_names(self) -> tuple[str, ...]:
        """列出窗口规则中的界面状态名称，配置不可用时返回空列表。"""
        return load_task_state_names(None, self._project_root) or ()

    def companion_selection(
        self, name: str = "", *, use_saved_plan: bool = False
    ) -> CompanionSelection:
        """运行时采用真实绑定，空闲时从选中任务或唯一共同声明选择目标。"""
        with self._run_lock:
            if self._current_run is not None:
                active = self._current_run.companion_selection()
                if active.running:
                    return active
        if use_saved_plan:
            plan = load_saved_run_plan(self._project_root)
            names = () if plan is None else tuple(item.name for item in plan.entries)
        else:
            names = (name,) if name else self.list_tasks()
        targets = {self._catalog.get(item).target for item in names}
        targets.discard(None)
        return CompanionSelection(
            False, target=next(iter(targets)) if len(targets) == 1 else None
        )

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
        """复用唯一运行槽启动单项任务，返回启动状态或已经占用该槽的会话状态。"""
        return self._start_tasks(
            (SavedPlanEntry(name),),
            dry_run=dry_run,
            dry_run_color=dry_run_color,
            dry_run_screen_state=dry_run_screen_state,
            dry_run_images=dry_run_images,
        )

    def describe_saved_plan(self) -> dict:
        """读取流程名称与顺序，逐项展示任务的依赖诊断。"""
        plan = load_saved_run_plan(self._project_root)
        if plan is None:
            return {}
        steps = []
        for index, entry in enumerate(plan.entries, 1):
            details = self.describe_task(entry.name)
            if details.exit_code:
                raise ValueError(
                    f"plan item {entry.name}: {details.stderr or details.readiness}"
                )
            delay = (
                f"，结束后等待 {entry.wait_after_seconds:g} 秒"
                if entry.wait_after_seconds
                else ""
            )
            steps.append(f"{index}. {entry.name}{delay}")
        return {**saved_run_plan_data(plan), "steps": steps}

    def read_saved_plan(self) -> dict:
        """返回原始流程条目，允许界面修复失效的任务引用。"""
        plan = load_saved_run_plan(self._project_root)
        return {} if plan is None else saved_run_plan_data(plan)

    def save_plan(self, plan: SavedRunPlan) -> dict:
        """空闲时校验完整任务引用并原子保存当前流程。"""
        with self._run_lock:
            if self._current_run is not None and self._current_run.snapshot().running:
                raise RuntimeError("a task is running; stop it before editing the plan")
            for entry in plan.entries:
                validate_task_resource_references(
                    self._task_with_shared_resources(self._catalog.get(entry.name))
                )
            save_run_plan(self._project_root, plan)
        return saved_run_plan_data(plan)

    def start_saved_plan(
        self,
        *,
        dry_run: bool,
        dry_run_color: str = "#000000",
        dry_run_screen_state: str = "未知",
    ) -> TaskRunStatus:
        """启动工作区保存的整套流程，复用单任务的运行槽与取消信号。"""
        try:
            plan = load_saved_run_plan(self._project_root)
            if plan is None:
                raise ValueError("no saved run plan in this workspace")
        except ValueError as exc:
            return TaskRunStatus(
                False, 2, stderr=str(exc), finish_reason="configuration_failed"
            )
        return self._start_tasks(
            plan.entries,
            dry_run=dry_run,
            dry_run_color=dry_run_color,
            dry_run_screen_state=dry_run_screen_state,
            dry_run_images=(),
            is_plan=True,
        )

    def start_plan(
        self,
        plan: SavedRunPlan,
        *,
        dry_run: bool,
        dry_run_color: str = "#000000",
        dry_run_screen_state: str = "未知",
    ) -> TaskRunStatus:
        """在同一运行锁内保存当前草稿并启动其冻结快照。"""
        return self._start_tasks(
            plan.entries,
            dry_run=dry_run,
            dry_run_color=dry_run_color,
            dry_run_screen_state=dry_run_screen_state,
            dry_run_images=(),
            is_plan=True,
            plan_to_save=plan,
        )

    def _start_tasks(
        self,
        entries: tuple[SavedPlanEntry, ...],
        *,
        dry_run: bool,
        dry_run_color: str,
        dry_run_screen_state: str,
        dry_run_images: tuple[str, ...],
        is_plan: bool = False,
        plan_to_save: SavedRunPlan | None = None,
    ) -> TaskRunStatus:
        """预先解析所有任务并启动同一个后台工作线程。"""
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
                    artifacts_path=current.artifacts_path,
                )
            archive = RunArchive(self._project_root, entries, dry_run=dry_run)
            session = _BackgroundScriptRun(archive)
            self._current_run = session
            try:
                items = []
                for entry in entries:
                    task = self._task_with_shared_resources(
                        self._catalog.get(entry.name)
                    )
                    if is_plan:
                        validate_task_resource_references(task)
                    images = dry_run_images
                    if dry_run and is_plan:
                        images = self.describe_task(entry.name).image_dependencies
                    items.append(
                        TaskPlanItem(entry.name, task, images, entry.wait_after_seconds)
                    )
                if plan_to_save is not None:
                    save_run_plan(self._project_root, plan_to_save)
            except TaskNotFoundError as exc:
                session.log.write_stderr(str(exc))
                session.finish(1, "task_not_found")
                return session.snapshot()
            except (LookupError, ValueError, OSError) as exc:
                session.log.write_stderr(f"task resource configuration failed: {exc}\n")
                session.finish(2, "configuration_failed")
                return session.snapshot()

            thread = threading.Thread(
                target=self._run_task_session,
                args=(
                    tuple(items),
                    dry_run,
                    dry_run_color,
                    dry_run_screen_state,
                    session,
                    is_plan,
                ),
                daemon=True,
            )
            self._run_thread = thread
            thread.start()
            return session.snapshot()

    def current_task_run(self) -> TaskRunStatus:
        """未启动过任务时返回空闲值，已有会话则返回其快照并保留完成结果。"""
        with self._run_lock:
            if self._current_run is None:
                return TaskRunStatus(running=False)
            return self._current_run.snapshot()

    def stop_running_task(self) -> TaskRunStatus:
        """设置当前会话的取消标记后立即返回快照，实际线程退出由等待接口确认。"""
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
        items: tuple[TaskPlanItem, ...],
        dry_run: bool,
        dry_run_color: str,
        dry_run_screen_state: str,
        session: _BackgroundScriptRun,
        is_plan: bool,
    ) -> None:
        """在后台线程中运行任务并写入会话状态。"""
        exit_code, finish_reason = 1, "failed"
        item_index = 0
        try:
            with (
                redirect_stdout(session.log.stdout_writer()),
                redirect_stderr(session.log.stderr_writer()),
            ):

                def run_item(item):
                    """运行一项独立窗口任务并记录顺序与结果。"""
                    if session.cancellation.is_cancelled():
                        return TaskPlanRunResult(130, "cancelled")
                    nonlocal item_index
                    item_index += 1
                    if session.archive is not None:
                        session.archive.start_item(item_index)
                    session.log.log(f"流程进度 {item_index}/{len(items)}")
                    session.log.log(f"开始任务 {item.name}")
                    outcome = run_task(
                        item.task,
                        dry_run=dry_run,
                        dry_run_color=dry_run_color,
                        dry_run_images=item.dry_run_images if dry_run else (),
                        dry_run_screen_state=dry_run_screen_state,
                        real_runtime_factory=(
                            None
                            if self._real_runtime_factory is None
                            else _TrackedRuntimeFactory(
                                self._real_runtime_factory, session
                            )
                        ),
                        cancellation_token=session.cancellation,
                        logger=session.log,
                        emit_step_events=True,
                        collect_diagnostics=True,
                    )
                    if session.archive is not None:
                        session.archive.finish_item(item_index, outcome)
                    if outcome.error_message:
                        session.log.write_stderr(f"{outcome.error_message}\n")
                    session.log.log(f"任务结束 {item.name} · {outcome.finish_reason}")
                    return TaskPlanRunResult(outcome.exit_code, outcome.finish_reason)

                def wait_after(seconds):
                    """在已关闭上一任务窗口会话后执行可取消等待。"""
                    if session.archive is not None:
                        session.archive.wait_after()
                    session.log.log(
                        f"任务后等待 {seconds:g} 秒"
                        + ("（模拟跳过实际等待）" if dry_run else "")
                    )
                    return (
                        not session.cancellation.is_cancelled()
                        if dry_run
                        else session.cancellation.wait(seconds)
                    )

                result = (
                    run_task_plan(items, run_item=run_item, wait=wait_after)
                    if is_plan
                    else run_item(items[0])
                )
            exit_code, finish_reason = result.exit_code, result.finish_reason
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
            if session.cancellation.is_cancelled():
                exit_code, finish_reason = 130, "cancelled"
            session.finish(exit_code, finish_reason)

    def _image_asset_root(self) -> Path:
        """返回本地 UI 允许读取模板图片的项目内目录。"""
        return image_asset_root(self._project_root)

    def _task_with_shared_resources(self, task: FunctionTask) -> FunctionTask:
        """按任务需要合并窗口规则里的共享搜索资源。"""
        return prepare_task_resources(task, self._project_root)
