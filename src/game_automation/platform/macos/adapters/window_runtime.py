"""为一次脚本运行绑定一个固定的 macOS 窗口与共享采集源。

本模块拥有会话资源，提供源证明与坐标边界；不解释脚本步骤、不复用观察界面的缓存。
显式原生后端失败时不会退回桌面输入或截图。
"""

from __future__ import annotations

import io
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
from game_automation.portable.application.runtime_ports import (
    RuntimePorts,
    RuntimeWindowIdentity,
)
from game_automation.portable.application.window_state_rules import (
    load_window_state_rules,
)
from game_automation.portable.domain import AreaWindow, Point, Rect
from game_automation.portable.engine.cancellation import TaskCancelledError


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
            from game_automation.platform.macos.adapters.task_window import (
                resolve_task_window,
            )

            backend = None if self._backend_factory is None else self._backend_factory()
            window, binding = resolve_task_window(
                target, backend=backend, binding_factory=self._binding_factory
            )
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
                    f"runtime backend={target.backend} pid={window.id.split(':', 1)[0]} window_id={binding.number} "
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


class SessionWindow:
    """按会话当前操作快照转换坐标，不保存启动时的矩形副本。"""

    def __init__(self, session):
        """借用执行线程拥有的窗口会话。"""
        self.session = session

    def resolve(self, point):
        """将任务局部点转换到本次操作的屏幕坐标。"""
        return AreaWindow(self.session.rect).resolve(point)

    def resolve_region(self, region):
        """将任务搜索范围转换到同一操作快照。"""
        return AreaWindow(self.session.rect).resolve_region(region)


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
        self._rect = window.rect
        self._operation_rect = None
        self._deferred_cause = None

    @property
    def rect(self):
        """返回有限操作固定的几何，空闲时返回最后采纳的位置。"""
        return self._operation_rect or self._rect

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
            SessionWindow(self),
            device,
            WindowColorReader(self) if requirements.needs_color_reader else None,
            WindowImageLocator(self) if requirements.needs_image_locator else None,
            WindowStateReader(self) if requirements.needs_screen_state_reader else None,
            control=self,
            window_identity=RuntimeWindowIdentity(
                int(self.window.id.split(":", 1)[0]), self.binding.number
            ),
            capture_diagnostic=self.capture_diagnostic,
        )

    def capture_diagnostic(self):
        """保存当前绑定窗口的最新有效源帧，绕过取消与恢复等待。"""
        if self._source is None:
            raise WindowCaptureError("运行窗口尚未建立采集源")
        deadline = self._clock() + 1.0
        while True:
            try:
                image = self._source.screenshot()
            except WindowFramePending:
                image = None
            if image is not None:
                try:
                    proof = getattr(self._source, "proof", None)
                    if (
                        proof is not None
                        and 0 <= self._clock() - proof.captured_at <= self._freshness
                        and (
                            self._after_input is None
                            or (
                                proof.sequence > self._after_sequence
                                and proof.captured_at > self._after_input
                            )
                        )
                    ):
                        output = io.BytesIO()
                        image.save(output, format="PNG")
                        return output.getvalue()
                finally:
                    image.close()
            if self._clock() >= deadline:
                raise WindowCaptureError("诊断截图等待首帧或输入后新鲜画面超时")
            self._sleep(0.02)

    def check_cancelled(self):
        """在每次系统边界与有界等待间保留取消优先。"""
        if self.cancellation is not None and self.cancellation.is_cancelled():
            raise TaskCancelledError("task run cancelled")

    def task_time(self):
        """只从任务预算扣除已识别的暂停，不改变系统事件时钟。"""
        now = self._clock() if self._paused_at is None else self._paused_at
        return now - self._paused_total

    def execute_input(self, action):
        """只重做未提交准备，已提交动作完成释放后再恢复。"""
        return self._execute_operation(action)

    def execute_observation(self, action):
        """将点位解析和画面解释置于同一可重试的有限观察中。"""
        return self._execute_operation(action)

    def _execute_operation(self, action):
        """嵌套读取借用外层快照，最外层拥有完整重试。"""
        if self._operation_rect is not None:
            return action()
        while True:
            self.check_window()
            self._operation_rect = self._rect
            self._input_phase = _InputPhase.PREPARING
            self._deferred_cause = None
            try:
                result = action()
                self.check_window()
            except _InputNotCommitted as exc:
                cause = exc.cause
            else:
                cause = self._deferred_cause
                if cause is None:
                    return result
            finally:
                committed = self._input_phase is _InputPhase.COMMITTED
                self._input_phase = None
                self._operation_rect = None
            self._recover(cause)
            if committed:
                return result

    def commit_input(self):
        """在系统按下调用之前标记提交，此后禁止重做准备回调。"""
        if self._input_phase is _InputPhase.PREPARING:
            self._input_phase = _InputPhase.COMMITTED

    def _check_geometry(self):
        """核对固定身份与本轮操作几何，不读取或等待源画面。"""
        self.check_cancelled()
        if self._closed:
            raise WindowCaptureError("原生运行会话已经关闭")
        item = self.binding.check()
        q = self.binding.quartz
        rect = self.rect
        expected = (rect.left, rect.top, rect.width, rect.height)
        current = logical_bounds(item.get(q.kCGWindowBounds, {}))
        if current != expected:
            raise WindowPresentationUnavailable(
                f"运行中目标窗口几何变化，原窗口={expected}，当前窗口={current}，等待新位置与画面稳定"
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
        """核对绑定窗口，前后台均可从平移恢复，后台还可等待短暂的展示中断。"""
        while True:
            try:
                return self._check_window_once()
            except WindowPresentationUnavailable as exc:
                if self._input_phase is _InputPhase.COMMITTED:
                    self._deferred_cause = exc
                    return {}
                self._presentation_unavailable(exc)

    def _presentation_unavailable(self, cause):
        """未提交操作退出后整体重做，空闲读取等待当前窗口恢复。"""
        if self.backend != "macos-window-background" and not self._position_changed():
            raise cause
        self._begin_pause(cause)
        if self._input_phase is _InputPhase.PREPARING:
            raise _InputNotCommitted(cause) from cause
        self._recover(cause)

    def _position_changed(self):
        """区分允许恢复的纯平移与前台后端原有终止故障。"""
        item = self.binding.check()
        bounds = logical_bounds(item.get(self.binding.quartz.kCGWindowBounds, {}))
        r = self.rect
        return (
            bounds is not None
            and bounds[2:] == (r.width, r.height)
            and bounds[:2] != (r.left, r.top)
        )

    def _adopt_position(self):
        """只采纳原绑定窗口的平移，尺寸仍由既有边界约束。"""
        item = self.binding.check()
        bounds = logical_bounds(item.get(self.binding.quartz.kCGWindowBounds, {}))
        if bounds is not None and bounds[2:] == (self._rect.width, self._rect.height):
            self._rect = Rect(*bounds)

    def current_rect(self):
        """读取同一绑定窗口当前矩形，供已提交事件与焦点核验使用。"""
        item = self.binding.check()
        bounds = logical_bounds(item.get(self.binding.quartz.kCGWindowBounds, {}))
        rect = self.rect
        if bounds is None or bounds[2:] != (rect.width, rect.height):
            raise WindowPresentationUnavailable("当前绑定窗口尺寸与任务素材不符")
        return Rect(*bounds)

    def release_point(self, local):
        """必要释放使用固定局部锚点，系统暂不可读时使用最后位置。"""
        rect = self.rect
        try:
            rect = self.current_rect()
        except Exception:
            pass
        return Point(rect.left + local.x, rect.top + local.y), rect

    def _begin_pause(self, cause):
        """一次暂停只记录一个开始点并撤销已有视觉证明。"""
        if self._paused_at is None:
            self._paused_at = self._clock()
            self.proof = None
            if self.logger is not None:
                self.logger.log(f"runtime paused backend={self.backend} reason={cause}")

    def _recover(self, cause):
        """保留唯一源，采纳稳定新位置并等更晚的源事件。"""
        self._begin_pause(cause)
        while True:
            self.check_cancelled()
            try:
                self._adopt_position()
                self._sleep(0.02)
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
        r = self.rect
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
