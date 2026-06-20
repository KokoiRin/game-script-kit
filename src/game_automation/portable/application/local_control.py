"""为本地控制 UI 提供应用层用例。

本 module 收敛 UI 需要的脚本列表、命名脚本运行和固定测试任务能力；它不渲染
HTML、不解析 HTTP，也不直接解释脚本步骤或创建平台自动化 adapter。
"""

from __future__ import annotations

import io
import subprocess
import sys
import threading
import time
from contextlib import redirect_stderr, redirect_stdout
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_FOLDER,
    IMAGE_ASSET_SUFFIXES,
    PROJECT_ROOT,
    SCREEN_STATE_CONFIG_NAME,
    image_asset_root,
    screen_state_config_path,
)
from game_automation.portable.application.config_script_loader import ScriptConfigError
from game_automation.portable.application.script_run import (
    InputDeviceFactory,
    PixelColorReaderFactory,
    ScreenImageLocatorFactory,
    run_script,
)
from game_automation.portable.application.screen_diagnostics import (
    ControlResult,
    ScreenCapture,
    ScreenCaptureFactory,
    ScreenDiagnosticsUseCase,
    ScreenImageBatchLocatorFactory,
    ScreenSizeFactory,
)
from game_automation.portable.application.screen_state_config import (
    ScreenStateConfigGroupSummary,
    load_screen_state_config_summary,
    load_screen_state_names,
)
from game_automation.portable.application.script_details import ScriptDetailsResult, describe_script_details
from game_automation.portable.application.script_resources import (
    load_shared_script_resources,
    script_with_shared_resources,
)
from game_automation.portable.domain import (
    Click,
    ImageTarget,
    ImageTemplate,
    Point,
    Rect,
    ScreenStateProbeResult,
    ScreenWindow,
    Script,
)
from game_automation.portable.engine.ports import (
    RunLogger,
    ScreenStateReader,
)
from game_automation.portable.scripts_manager import DEFAULT_SCRIPT_CATALOG
from game_automation.portable.scripts_manager.catalog import ScriptCatalog, ScriptNotFoundError

CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]

@dataclass(frozen=True, slots=True)
class ScriptRunStatus:
    running: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True, slots=True)
class ScreenStateConfigSummaryResult:
    exit_code: int
    groups: tuple[ScreenStateConfigGroupSummary, ...] = ()
    stderr: str = ""


@dataclass(frozen=True, slots=True)
class ScreenStateProbeStats:
    rounds: int = 0
    last_elapsed_ms: float | None = None
    matched_counts: tuple[tuple[str, int], ...] = ()
    skipped_counts: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class ScreenStateProbeCandidateSummary:
    name: str
    status: str
    elapsed_ms: float
    confidence: float | None = None
    search_name: str | None = None
    best_confidence: float | None = None
    best_rect: Rect | None = None


@dataclass(frozen=True, slots=True)
class ScreenStateProbeStatus:
    running: bool
    current_state: str = "未知"
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    hints: tuple[str, ...] = ()
    stats: ScreenStateProbeStats = ScreenStateProbeStats()
    candidates: tuple[ScreenStateProbeCandidateSummary, ...] = ()


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

    def stdout_writer(self):
        """返回用于重定向 stdout 的 writer。"""
        return _RunLogWriter(self.write_stdout)

    def stderr_writer(self):
        """返回用于重定向 stderr 的 writer。"""
        return _RunLogWriter(self.write_stderr)

    def log(self, message: str) -> None:
        """把运行诊断日志追加到 stdout。"""
        self.write_stdout(f"{message}\n")

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


class _LocalScreenStateReader(ScreenStateReader):
    def __init__(self, app: "LocalControlApplication") -> None:
        """保存本地控制用例，用现有状态探测能力读取当前状态。"""
        self._app = app

    def read_current_state(
        self,
        *,
        min_confidence: float = 0.8,
        logger: RunLogger | None = None,
    ) -> str:
        """执行一轮状态探测并返回当前状态名称。"""
        background_state = self._app._running_background_screen_state()
        if background_state is not None:
            if logger is not None:
                logger.log(
                    "screen state reader reused background probe "
                    f"current_state={background_state}"
                )
            return background_state

        result = self._app.probe_screen_state_once(
            min_confidence=min_confidence,
            logger=logger,
        )
        if logger is not None:
            _log_screen_state_probe_result(logger, result)
        return result.current_state


class _BackgroundScriptRun:
    def __init__(self) -> None:
        """初始化后台脚本会话状态。"""
        self.cancellation = _CancellationFlag()
        self.log = _ThreadSafeRunLog()
        self._lock = threading.Lock()
        self._running = True
        self._exit_code: int | None = None

    def finish(self, exit_code: int) -> None:
        """记录后台脚本结束状态。"""
        with self._lock:
            self._running = False
            self._exit_code = exit_code

    def snapshot(self) -> ScriptRunStatus:
        """返回后台脚本当前状态快照。"""
        stdout, stderr = self.log.snapshot()
        with self._lock:
            return ScriptRunStatus(
                running=self._running,
                exit_code=self._exit_code,
                stdout=stdout,
                stderr=stderr,
            )


class _BackgroundScreenStateProbe:
    def __init__(self) -> None:
        """初始化后台界面状态探测会话。"""
        self.cancellation = _CancellationFlag()
        self.log = _ThreadSafeRunLog()
        self._lock = threading.Lock()
        self._running = True
        self._current_state = "未知"
        self._exit_code: int | None = None
        self._rounds = 0
        self._last_elapsed_ms: float | None = None
        self._matched_counts: dict[str, int] = {}
        self._skipped_counts: dict[str, int] = {}
        self._hints: tuple[str, ...] = ()
        self._candidates: tuple[ScreenStateProbeCandidateSummary, ...] = ()

    def record_result(self, result: ScreenStateProbeResult) -> None:
        """记录最近一轮界面状态探测结果并累计会话统计。"""
        with self._lock:
            self._current_state = result.current_state
            self._rounds += 1
            self._last_elapsed_ms = result.elapsed_ms
            if result.known:
                self._matched_counts[result.current_state] = (
                    self._matched_counts.get(result.current_state, 0) + 1
                )
            for candidate in result.candidates:
                if candidate.skipped:
                    name = candidate.candidate.name
                    self._skipped_counts[name] = self._skipped_counts.get(name, 0) + 1
            self._hints = result.hints
            self._candidates = tuple(
                _probe_candidate_summary(candidate)
                for candidate in result.candidates
            )

    def finish(self, exit_code: int) -> None:
        """记录后台界面状态探测结束状态。"""
        with self._lock:
            self._running = False
            self._exit_code = exit_code

    def snapshot(self) -> ScreenStateProbeStatus:
        """返回后台界面状态探测当前状态快照。"""
        stdout, stderr = self.log.snapshot()
        with self._lock:
            return ScreenStateProbeStatus(
                running=self._running,
                current_state=self._current_state,
                exit_code=self._exit_code,
                stdout=stdout,
                stderr=stderr,
                hints=self._hints,
                stats=ScreenStateProbeStats(
                    rounds=self._rounds,
                    last_elapsed_ms=self._last_elapsed_ms,
                    matched_counts=tuple(self._matched_counts.items()),
                    skipped_counts=tuple(self._skipped_counts.items()),
                ),
                candidates=self._candidates,
            )


class LocalControlApplication:
    def __init__(
        self,
        catalog: ScriptCatalog = DEFAULT_SCRIPT_CATALOG,
        *,
        script_config_errors: tuple[ScriptConfigError, ...] = (),
        command_runner: CommandRunner | None = None,
        project_root: Path = PROJECT_ROOT,
        real_device_factory: InputDeviceFactory | None = None,
        real_color_reader_factory: PixelColorReaderFactory | None = None,
        real_image_locator_factory: ScreenImageLocatorFactory | None = None,
        real_image_batch_locator_factory: ScreenImageBatchLocatorFactory | None = None,
        screen_capture_factory: ScreenCaptureFactory | None = None,
        screen_size_factory: ScreenSizeFactory | None = None,
    ) -> None:
        """注入 UI 用例需要的脚本 catalog、项目路径和外部能力工厂。"""
        self._catalog = catalog
        self._script_config_errors = script_config_errors
        self._command_runner = command_runner if command_runner is not None else _run_command
        self._project_root = project_root
        self._real_device_factory = real_device_factory
        self._real_color_reader_factory = real_color_reader_factory
        self._real_image_locator_factory = real_image_locator_factory
        self._screen_diagnostics = ScreenDiagnosticsUseCase(
            project_root=project_root,
            real_image_locator_factory=real_image_locator_factory,
            real_image_batch_locator_factory=real_image_batch_locator_factory,
            screen_capture_factory=screen_capture_factory,
            screen_size_factory=screen_size_factory,
        )
        self._run_lock = threading.Lock()
        self._current_run: _BackgroundScriptRun | None = None
        self._probe_lock = threading.Lock()
        self._current_probe: _BackgroundScreenStateProbe | None = None
        self._test_tasks: dict[str, tuple[str, ...]] = {
            "all": (sys.executable, "-m", "pytest"),
        }

    def list_scripts(self) -> tuple[str, ...]:
        """返回 UI 可展示的脚本名称列表。"""
        return self._catalog.list_names()

    def list_script_config_errors(self) -> tuple[ScriptConfigError, ...]:
        """返回文件脚本加载时被隔离的配置错误。"""
        return self._script_config_errors

    def image_asset_folder_label(self) -> str:
        """返回用户应放置模板图片的项目内目录名。"""
        return IMAGE_ASSET_FOLDER

    def list_image_assets(self) -> tuple[str, ...]:
        """列出项目图片资源目录中的可用模板图片。"""
        asset_root = self._image_asset_root()
        if not asset_root.is_dir():
            return ()
        return tuple(
            sorted(
                path.name
                for path in asset_root.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_ASSET_SUFFIXES
            )
        )

    def list_screen_state_names(self) -> tuple[str, ...]:
        """列出状态配置中的界面状态名称，配置不可用时返回空列表。"""
        try:
            names = load_screen_state_names(self._image_asset_root() / SCREEN_STATE_CONFIG_NAME)
        except ValueError:
            return ()
        return () if names is None else names

    def describe_screen_state_config(self) -> ScreenStateConfigSummaryResult:
        """返回 UI 可展示的界面状态配置摘要。"""
        try:
            groups = load_screen_state_config_summary(
                self._image_asset_root() / SCREEN_STATE_CONFIG_NAME,
                asset_root=self._image_asset_root(),
                supported_suffixes=IMAGE_ASSET_SUFFIXES,
            )
        except (LookupError, ValueError) as exc:
            return ScreenStateConfigSummaryResult(exit_code=2, stderr=f"{exc}\n")
        return ScreenStateConfigSummaryResult(exit_code=0, groups=() if groups is None else groups)

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
            return ControlResult(exit_code=1, stderr=str(exc))
        except (LookupError, ValueError) as exc:
            return ControlResult(exit_code=2, stderr=f"script resource configuration failed: {exc}\n")

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
                real_screen_state_reader_factory=self._build_screen_state_reader,
                logger=_StringRunLogger(stdout),
            )

        if result.error_message is not None:
            stderr.write(result.error_message)
            stderr.write("\n")
        return ControlResult(
            exit_code=result.exit_code,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
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
                )
            try:
                script = self._script_with_shared_resources(self._catalog.get(name))
            except ScriptNotFoundError as exc:
                return ScriptRunStatus(running=False, exit_code=1, stderr=str(exc))
            except (LookupError, ValueError) as exc:
                return ScriptRunStatus(
                    running=False,
                    exit_code=2,
                    stderr=f"script resource configuration failed: {exc}\n",
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

    def click_image_asset(
        self,
        asset_name: str,
        *,
        dry_run: bool,
        min_confidence: float = 0.8,
    ) -> ControlResult:
        """把项目图片资源作为模板目标，运行一次查找并点击脚本。"""
        try:
            asset_path = self._resolve_image_asset(asset_name)
            script = Script(
                name="click-image-asset",
                window=ScreenWindow(),
                steps=(
                    Click(
                        ImageTarget(
                            ImageTemplate(str(asset_path)),
                            min_confidence=min_confidence,
                        )
                    ),
                ),
            )
        except ValueError as exc:
            return ControlResult(exit_code=2, stderr=f"invalid image click request: {exc}\n")

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = run_script(
                script,
                dry_run=dry_run,
                dry_run_images=(str(asset_path),) if dry_run else (),
                real_device_factory=self._real_device_factory,
                real_image_locator_factory=self._real_image_locator_factory,
                real_screen_state_reader_factory=self._build_screen_state_reader,
                logger=_StringRunLogger(stdout),
            )

        if result.error_message is not None:
            stderr.write(result.error_message)
            stderr.write("\n")
        return ControlResult(
            exit_code=result.exit_code,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def probe_screen_state_once(
        self,
        *,
        min_confidence: float = 0.8,
        logger: RunLogger | None = None,
    ) -> ScreenStateProbeResult:
        """使用项目图片资源执行一轮界面状态探测。"""
        return self._screen_diagnostics.probe_screen_state_once(
            min_confidence=min_confidence,
            logger=logger,
        )

    def build_screen_state_reader(self) -> ScreenStateReader:
        """创建可供脚本运行时复用的界面状态读取端口。"""
        return _LocalScreenStateReader(self)

    def start_screen_state_probe(
        self,
        *,
        min_confidence: float = 0.8,
        interval_seconds: float = 1.0,
    ) -> ScreenStateProbeStatus:
        """启动后台界面状态循环探测会话。"""
        with self._probe_lock:
            if self._current_probe is not None and self._current_probe.snapshot().running:
                current = self._current_probe.snapshot()
                return ScreenStateProbeStatus(
                    running=current.running,
                    current_state=current.current_state,
                    exit_code=current.exit_code,
                    stdout=current.stdout,
                    stderr=current.stderr + "screen state probe is already running\n",
                )

            session = _BackgroundScreenStateProbe()
            self._current_probe = session
            thread = threading.Thread(
                target=self._run_screen_state_probe_session,
                args=(min_confidence, interval_seconds, session),
                daemon=True,
            )
            thread.start()
            return session.snapshot()

    def current_screen_state_probe(self) -> ScreenStateProbeStatus:
        """返回当前后台界面状态探测状态。"""
        with self._probe_lock:
            if self._current_probe is None:
                return ScreenStateProbeStatus(running=False)
            return self._current_probe.snapshot()

    def stop_screen_state_probe(self) -> ScreenStateProbeStatus:
        """请求停止当前后台界面状态探测。"""
        with self._probe_lock:
            if self._current_probe is None:
                return ScreenStateProbeStatus(
                    running=False,
                    exit_code=0,
                    stderr="no screen state probe is running\n",
                )
            self._current_probe.cancellation.cancel()
            return self._current_probe.snapshot()

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
                real_screen_state_reader_factory=self._build_screen_state_reader,
                cancellation_token=session.cancellation,
                logger=session.log,
            )
        if result.error_message is not None:
            session.log.write_stderr(f"{result.error_message}\n")
        session.finish(result.exit_code)

    def _run_screen_state_probe_session(
        self,
        min_confidence: float,
        interval_seconds: float,
        session: _BackgroundScreenStateProbe,
    ) -> None:
        """在后台线程中循环探测界面状态并写入会话日志。"""
        try:
            while not session.cancellation.is_cancelled():
                result = self.probe_screen_state_once(
                    min_confidence=min_confidence,
                    logger=session.log,
                )
                session.record_result(result)
                _log_screen_state_probe_result(session.log, result)
                _wait_for_next_probe_round(session.cancellation, interval_seconds)
            session.finish(0)
        except Exception as exc:
            session.log.write_stderr(f"{exc}\n")
            session.finish(1)

    def capture_screen_screenshot(self) -> ControlResult:
        """保存一张真实屏幕截图，供 UI 诊断截图权限和画面内容。"""
        return self._screen_diagnostics.capture_screen_screenshot()

    def diagnose_screen_setup(self, *, min_confidence: float = 0.8) -> ControlResult:
        """组合截图诊断和单轮状态探测，帮助用户判断屏幕识别环境。"""
        return self._screen_diagnostics.diagnose_screen_setup(min_confidence=min_confidence)

    def capture_screen_region_diagnostics(self) -> ControlResult:
        """保存一张带状态识别区域框的诊断截图。"""
        return self._screen_diagnostics.capture_screen_region_diagnostics()

    def capture_screen_probe_diagnostics(self, *, min_confidence: float = 0.8) -> ControlResult:
        """保存一张带状态探测候选最佳位置框的诊断截图。"""
        return self._screen_diagnostics.capture_screen_probe_diagnostics(
            min_confidence=min_confidence,
        )

    def capture_screen_region_crops(self) -> ControlResult:
        """保存当前屏幕中每个状态识别命名区域的裁剪图。"""
        return self._screen_diagnostics.capture_screen_region_crops()

    def capture_screen_probe_crops(self, *, min_confidence: float = 0.8) -> ControlResult:
        """保存一轮状态探测候选最佳位置裁剪图。"""
        return self._screen_diagnostics.capture_screen_probe_crops(
            min_confidence=min_confidence,
        )

    def latest_screen_screenshot_path(self) -> Path:
        """返回最近一次截屏诊断保存的项目内文件路径。"""
        return self._screen_diagnostics.latest_screen_screenshot_path()

    def latest_screen_region_diagnostics_path(self) -> Path:
        """返回最近一次区域诊断截图保存的项目内文件路径。"""
        return self._screen_diagnostics.latest_screen_region_diagnostics_path()

    def latest_screen_probe_diagnostics_path(self) -> Path:
        """返回最近一次探测诊断截图保存的项目内文件路径。"""
        return self._screen_diagnostics.latest_screen_probe_diagnostics_path()

    def latest_screen_region_crop_folder(self) -> Path:
        """返回最近一次命名区域裁剪图保存的项目内目录。"""
        return self._screen_diagnostics.latest_screen_region_crop_folder()

    def latest_screen_probe_crop_folder(self) -> Path:
        """返回最近一次探测候选裁剪图保存的项目内目录。"""
        return self._screen_diagnostics.latest_screen_probe_crop_folder()

    def run_tests(self, task_name: str = "all") -> ControlResult:
        """运行白名单测试任务，并返回 UI 可展示的执行结果。"""
        command = self._test_tasks.get(task_name)
        if command is None:
            return ControlResult(
                exit_code=2,
                stderr=f"unknown test task: {task_name}\n",
            )

        completed = self._command_runner(command, self._project_root)
        return ControlResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _image_asset_root(self) -> Path:
        """返回本地 UI 允许读取模板图片的项目内目录。"""
        return image_asset_root(self._project_root)

    def _resolve_image_asset(self, asset_name: str) -> Path:
        """解析并校验图片资源必须位于项目 assets 目录内。"""
        candidate = (self._image_asset_root() / asset_name).resolve()
        asset_root = self._image_asset_root().resolve()
        try:
            candidate.relative_to(asset_root)
        except ValueError as exc:
            raise ValueError("image asset must stay inside assets folder") from exc
        if not candidate.is_file() or candidate.suffix.lower() not in IMAGE_ASSET_SUFFIXES:
            raise ValueError("image asset does not exist or has unsupported suffix")
        return candidate

    def _build_screen_state_reader(self) -> ScreenStateReader:
        """创建基于当前本地控制配置的界面状态 reader。"""
        return self.build_screen_state_reader()

    def _running_background_screen_state(self) -> str | None:
        """返回运行中后台探测的有效状态，没有可用状态时返回 None。"""
        with self._probe_lock:
            if self._current_probe is None or self._current_probe.cancellation.is_cancelled():
                return None
            status = self._current_probe.snapshot()
        if not status.running or status.current_state == "未知":
            return None
        return status.current_state

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

def _log_screen_state_probe_result(logger: RunLogger, result: ScreenStateProbeResult) -> None:
    """记录一轮界面状态探测摘要，供 UI 日志展示。"""
    logger.log(
        "screen state probe round "
        f"current_state={result.current_state} "
        f"elapsed_ms={result.elapsed_ms:.2f}"
    )
    for candidate in result.candidates:
        logger.log(
            "screen state candidate "
            f"candidate={candidate.candidate.name} "
            f"found={candidate.found} "
            f"confidence={candidate.confidence} "
            f"best_confidence={candidate.best_confidence} "
            f"best_rect={candidate.best_rect} "
            f"elapsed_ms={candidate.elapsed_ms:.2f}"
        )


def _probe_candidate_summary(candidate) -> ScreenStateProbeCandidateSummary:
    """把领域候选结果转换成 UI 用例状态快照摘要。"""
    if candidate.skipped:
        status = "skipped"
    elif candidate.found:
        status = "matched"
    else:
        status = "missed"
    return ScreenStateProbeCandidateSummary(
        name=candidate.candidate.name,
        status=status,
        elapsed_ms=candidate.elapsed_ms,
        confidence=candidate.confidence,
        search_name=candidate.candidate.search_name,
        best_confidence=candidate.best_confidence,
        best_rect=candidate.best_rect,
    )


def _wait_for_next_probe_round(cancellation: _CancellationFlag, interval_seconds: float) -> None:
    """等待下一轮探测间隔，同时允许停止请求尽快生效。"""
    deadline = time.monotonic() + max(0, interval_seconds)
    while time.monotonic() < deadline and not cancellation.is_cancelled():
        time.sleep(min(0.05, deadline - time.monotonic()))


def _run_command(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """执行 application 层白名单命令，不经过 shell。"""
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
