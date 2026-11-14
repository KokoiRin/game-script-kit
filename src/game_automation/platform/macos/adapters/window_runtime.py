"""为一次脚本运行绑定一个固定的 macOS 窗口与共享采集源。

本模块拥有会话资源，提供源证明与坐标边界；不解释脚本步骤、不复用观察界面的缓存。
显式原生后端失败时不会退回桌面输入或截图。
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from enum import Enum, auto
from pathlib import Path

from game_automation.platform.macos.adapters.window_identity import (
    BoundWindow,
    WindowPresentationUnavailable,
    logical_bounds,
)
from game_automation.platform.macos.adapters.window_stream import (
    WindowFramePending,
    WindowStreamSource,
)
from game_automation.portable.application.capture_errors import WindowCaptureError
from game_automation.portable.application.runtime_ports import RuntimePorts
from game_automation.portable.application.window_state_rules import (
    load_window_state_rules,
)
from game_automation.portable.domain import AreaWindow
from game_automation.portable.engine.cancellation import TaskCancelledError
from game_automation.portable.preparation.models import DesktopWindow


class NativeRuntimeLease:
    """进程级互斥与失败资源强引用，不拥有正常会话的图像缓存。"""

    def __init__(self):
        """创建可注入的独立租约；生产默认使用本模块的进程单例。"""
        self._lock = threading.Lock()
        self._leased = False
        self._close_error = None
        self._failed_session = None

    def acquire(self):
        """关闭失败后拒绝所有工作区和工厂，直到后台进程重启。"""
        with self._lock:
            if self._close_error is not None:
                raise RuntimeError(
                    f"macos-window session unavailable: {self._close_error}; 请重新启动后台后重试"
                )
            if self._leased:
                raise RuntimeError("已有原生脚本运行，请等待当前会话停止")
            self._leased = True

    def release(self):
        """只有系统停流成功后才能交还进程租约。"""
        with self._lock:
            self._leased = False

    def fail_close(self, session, error):
        """保留失败会话与源的强引用，不因工厂或工作区销毁而丢失。"""
        with self._lock:
            self._close_error = str(error)[:1024]
            self._failed_session = session


_PROCESS_LEASE = NativeRuntimeLease()


class MacOSRuntimeFactory:
    """一次只拥有一个原生会话，停流失败后保留租约直到应用重启。"""

    def __init__(
        self,
        workspace: Path,
        *,
        backend_factory=None,
        binding_factory=BoundWindow,
        source_factory=WindowStreamSource,
        session_factory=None,
        lease=None,
    ):
        """保存工作区与系统边界；构造工厂本身不触发系统权限。"""
        self.workspace = Path(workspace)
        self._backend_factory = backend_factory
        self._binding_factory = binding_factory
        self._source_factory = source_factory
        self._session_factory = session_factory
        self._lease = _PROCESS_LEASE if lease is None else lease

    @contextmanager
    def open(self, target, requirements, cancellation, logger):
        """选取唯一标题窗口并管理整轮输入、识图和停流。"""
        self._lease.acquire()
        session = None
        try:
            if not target.uses_native_window:
                raise ValueError(
                    "macOS runtime requires an explicit native-window backend"
                )
            rules = load_window_state_rules(self.workspace)
            if (rules.width, rules.height) != (target.width, target.height):
                raise ValueError("目标窗口尺寸与状态素材不符")
            if self._backend_factory is None:
                from game_automation.platform.macos.adapters.accessibility_window_backend import (
                    MacOSAccessibilityWindowBackend,
                )

                backend = MacOSAccessibilityWindowBackend()
            else:
                backend = self._backend_factory()
            matches = [
                w
                for w in backend.list_windows(target.application)
                if w.title == target.window_title
            ]
            if len(matches) != 1:
                raise WindowCaptureError(
                    "目标窗口标题必须唯一且可见，请打开指定游戏窗口"
                )
            selected = matches[0]
            if (selected.rect.width, selected.rect.height) != (
                target.width,
                target.height,
            ):
                raise ValueError("目标窗口尺寸与脚本素材不符，请恢复窗口尺寸后重试")
            window = DesktopWindow(
                f"{selected.pid}:{selected.window_number}",
                target.application,
                selected.title,
                selected.rect,
            )
            binding = self._binding_factory(window)
            factory = (
                MacOSWindowSession
                if self._session_factory is None
                else self._session_factory
            )
            # 先登记会话，再分配可能启动的资源，失败也必须进入同一关闭路径。
            session = factory(
                window,
                binding,
                rules,
                cancellation=cancellation,
                logger=logger,
                backend=target.backend,
            )
            source = self._source_factory(
                window, (rules.pixel_width, rules.pixel_height), hz=5, binding=binding
            )
            session.attach_source(source)
            if logger is not None:
                logger.log(
                    f"runtime backend={target.backend} pid={selected.pid} window_id={binding.number} "
                    f"title={window.title!r} fixed_rect={window.rect} pixel_size={(rules.pixel_width, rules.pixel_height)} hz=5"
                )
            yield session.ports(requirements)
        finally:
            try:
                if session is not None:
                    session.close()
            except BaseException as exc:
                self._lease.fail_close(session, exc)
                raise
            else:
                self._lease.release()


class _InputPhase(Enum):
    """区分可重新定位的准备与不可重放的已尝试按下。"""

    PREPARING = auto()
    COMMITTED = auto()


class _InputNotCommitted(WindowCaptureError):
    """仅在尚未尝试按下时要求重新定位，永不跨越已发送输入。"""

    def __init__(self, cause):
        """保留平台暂态原因供会话恢复。"""
        super().__init__(str(cause))
        self.cause = cause


class MacOSWindowSession:
    """统一固定窗口身份、输入后新帧门槛与唯一源所有权。"""

    capture_mode = "window_stream"

    def __init__(
        self,
        window,
        binding,
        rules,
        *,
        cancellation=None,
        logger=None,
        clock=time.monotonic,
        sleep=time.sleep,
        freshness_seconds=1.0,
        capture_timeout=2.0,
        backend="macos-window",
    ):
        """保存固定几何，系统源在工厂登记会话之后注入。"""
        self.window, self.binding, self.rules = window, binding, rules
        self.backend = backend
        self.cancellation, self.logger = cancellation, logger
        self._clock, self._sleep = clock, sleep
        self._freshness, self._capture_timeout = freshness_seconds, capture_timeout
        self._source = None
        self._closed = False
        self.proof = None
        self._after_input = None
        self._after_sequence = 0
        self._paused_at = None
        self._paused_total = 0.0
        self._input_phase = None

    def attach_source(self, source):
        """仅绑定本会话独占的源，禁止运行中替换。"""
        if self._source is not None:
            raise RuntimeError("native capture source already attached")
        self._source = source

    def ports(self, requirements):
        """按本轮需求装配端口，全部只引用同一会话。"""
        from game_automation.platform.macos.adapters.window_input import (
            MacOSWindowInputDevice,
        )
        from game_automation.platform.macos.adapters.window_vision import (
            WindowColorReader,
            WindowImageLocator,
            WindowStateReader,
        )

        if self.backend == "macos-window-background":
            from game_automation.platform.macos.adapters.window_background_input import (
                MacOSBackgroundWindowInputDevice,
            )

            device = MacOSBackgroundWindowInputDevice(self)
        else:
            device = MacOSWindowInputDevice(self)
        return RuntimePorts(
            AreaWindow(self.window.rect),
            device,
            WindowColorReader(self) if requirements.needs_color_reader else None,
            WindowImageLocator(self) if requirements.needs_image_locator else None,
            WindowStateReader(self) if requirements.needs_screen_state_reader else None,
            control=self if self.backend == "macos-window-background" else None,
        )

    def check_cancelled(self):
        """在每次系统边界与有界等待间保留取消优先。"""
        if self.cancellation is not None and self.cancellation.is_cancelled():
            raise TaskCancelledError("task run cancelled")

    def task_time(self):
        """只从任务预算扣除已识别的暂停，不改变系统事件时钟。"""
        now = self._clock() if self._paused_at is None else self._paused_at
        return now - self._paused_total

    def execute_input(self, action):
        """仅重做按下前的完整准备，提交后保留当前调用栈。"""
        while True:
            self.check_window()
            self._input_phase = _InputPhase.PREPARING
            try:
                return action()
            except _InputNotCommitted as exc:
                cause = exc.cause
            finally:
                self._input_phase = None
            self._recover(cause)

    def commit_input(self):
        """在系统按下调用之前标记提交，此后禁止重做准备回调。"""
        if self._input_phase is _InputPhase.PREPARING:
            self._input_phase = _InputPhase.COMMITTED

    def _check_geometry(self):
        """核对固定身份和完整原矩形，不读取或等待源画面。"""
        self.check_cancelled()
        if self._closed:
            raise WindowCaptureError("原生运行会话已经关闭")
        item = self.binding.check()
        q = self.binding.quartz
        rect = self.window.rect
        expected = (rect.left, rect.top, rect.width, rect.height)
        current = logical_bounds(item.get(q.kCGWindowBounds, {}))
        if current != expected:
            advice = (
                "请恢复原窗口"
                if self.backend == "macos-window-background"
                else "请停止后重新运行"
            )
            raise WindowPresentationUnavailable(
                f"运行中目标窗口位置已变化，原窗口={expected}，当前窗口={current}，{advice}"
            )
        return item

    def _check_window_once(self):
        """先核对完整矩形，后台另读轻量源证明并复核首帧超时。"""
        item = self._check_geometry()
        if self.backend == "macos-window-background" and self._source is not None:
            try:
                proof = self._source.check_available()
            except WindowFramePending:
                self._check_geometry()
                raise
            if (
                proof is None
                or not 0 <= self._clock() - proof.captured_at <= self._freshness
            ):
                raise WindowPresentationUnavailable(
                    "窗口流暂未提供有效新画面，等待恢复"
                )
        return item

    def check_window(self):
        """后台等待短暂展示变化，其他模式维持立即报告错误。"""
        while True:
            try:
                return self._check_window_once()
            except WindowPresentationUnavailable as exc:
                self._presentation_unavailable(exc)

    def _presentation_unavailable(self, cause):
        """准备区退出后重新定位，其余调用在原位置等待恢复。"""
        if self.backend != "macos-window-background":
            raise cause
        self._begin_pause(cause)
        if self._input_phase is _InputPhase.PREPARING:
            raise _InputNotCommitted(cause) from cause
        self._recover(cause)

    def _begin_pause(self, cause):
        """一次暂停只记录一个开始点并撤销已有视觉证明。"""
        if self._paused_at is None:
            self._paused_at = self._clock()
            self.proof = None
            if self.logger is not None:
                self.logger.log(f"runtime paused backend={self.backend} reason={cause}")

    def _recover(self, cause):
        """保留唯一源，等原几何和恢复之后的源事件再继续。"""
        self._begin_pause(cause)
        while True:
            self.check_cancelled()
            try:
                self._check_window_once()
                restored_at = self._clock()
                sequence = getattr(getattr(self._source, "proof", None), "sequence", 0)
                with self._read_frame(after_time=restored_at, after_sequence=sequence):
                    pass
            except WindowPresentationUnavailable:
                self._sleep(0.02)
                continue
            paused_seconds = self._clock() - self._paused_at
            self._paused_total += paused_seconds
            self._paused_at = None
            if self.logger is not None:
                self.logger.log(
                    f"runtime resumed backend={self.backend} paused_seconds={paused_seconds:.3f}"
                )
            return

    def validate_point(self, point):
        """校验全局逻辑点必须在已绑定窗口内。"""
        self.check_window()
        r = self.window.rect
        if not (
            r.left <= point.x < r.left + r.width and r.top <= point.y < r.top + r.height
        ):
            raise ValueError("输入或取色坐标超出固定目标窗口")

    def input_finished(self):
        """输入结束后要求新的系统源事件，重复缓存不能证明输入结果。"""
        source_proof = getattr(self._source, "proof", None)
        self._after_sequence = max(
            self._after_sequence, getattr(source_proof, "sequence", 0)
        )
        self._after_input = self._clock()

    def screenshot(self):
        """返回有效窗口帧，后台暂态只恢复当前读取而不重放步骤。"""
        while True:
            try:
                return self._read_frame()
            except WindowPresentationUnavailable as exc:
                self._presentation_unavailable(exc)

    def _read_frame(self, *, after_time=None, after_sequence=0):
        """用真实时间有界等待新帧，并同时核对输入与恢复屏障。"""
        deadline = self._clock() + self._capture_timeout
        while True:
            self._check_window_once()
            image = self._source.screenshot()
            try:
                self._check_window_once()
                if image.size != (self.rules.pixel_width, self.rules.pixel_height):
                    raise WindowPresentationUnavailable("窗口截图像素尺寸与素材不符")
                proof = getattr(self._source, "proof", None)
                now = self._clock()
                fresh = (
                    proof is not None
                    and 0 <= now - proof.captured_at <= self._freshness
                )
                after_input = self._after_input is None or (
                    proof is not None
                    and proof.sequence > self._after_sequence
                    and proof.captured_at > self._after_input
                )
                after_recovery = after_time is None or (
                    proof is not None
                    and proof.sequence > after_sequence
                    and proof.captured_at > after_time
                )
                if fresh and after_input and after_recovery:
                    self.proof = proof
                    self._after_input = None
                    return image
            except BaseException:
                image.close()
                raise
            image.close()
            if self._clock() >= deadline:
                error = (
                    WindowPresentationUnavailable
                    if self.backend == "macos-window-background"
                    else WindowCaptureError
                )
                raise error(
                    "未获得输入之后的新窗口画面，或窗口流已过期；请检查游戏和截图权限"
                )
            self.check_cancelled()
            self._sleep(0.02)

    def size(self):
        """向匹配器提供窗口逻辑尺寸。"""
        return self.window.rect.width, self.window.rect.height

    def close(self):
        """仅在系统停流和回调屏障成功后释放会话。"""
        if not self._closed:
            if self._source is not None:
                self._source.close()
            self._closed = True
            self.proof = None
